from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from core.enums import QUESTION_TYPE_LABELS, SurveyStatus
from core.exceptions import SmartSurveyException
from services import quality_rules
from services.analysis_service import AnalysisService
from services.quality_service import QualityService
from services.survey_service import SurveyService

# The flag order of board W-04, which is not the order of quality_rules.FLAG_CODES.
QUALITY_FLAG_ORDER = (
    quality_rules.ATTENTION_FAILED,
    quality_rules.SPEEDING,
    quality_rules.DUPLICATE_DEVICE,
    quality_rules.STRAIGHT_LINING,
    quality_rules.SIGNALS_MISSING,
)
# The flags whose "Not checked" reason the panel can state; an empty device hash implies
# missing signals, and SIGNALS_MISSING is always checked.
QUALITY_NOT_CHECKED_CODES = (
    quality_rules.ATTENTION_FAILED,
    quality_rules.SPEEDING,
    quality_rules.STRAIGHT_LINING,
)
# Board W-05b: the "Compare groups by" options; the service accepts the non-empty values.
GROUP_BY_OPTIONS = (
    ("", "No breakdown"),
    ("gender", "Gender"),
    ("age", "Age group"),
    ("governorate", "Governorate"),
)
GROUP_BY_HEADINGS = {
    "gender": "By gender",
    "age": "By age group",
    "governorate": "By governorate",
}
SENTIMENT_NAMES = (("positive", "Positive"), ("neutral", "Neutral"), ("negative", "Negative"))


def analytics_dashboard(request, survey_id):
    """Render provider survey analytics using SurveyService, AnalysisService and QualityService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        survey = SurveyService().get_provider_survey(request.user, survey_id)
        results = AnalysisService().get_survey_results(
            request.user,
            survey_id,
            group_by=request.GET.get("group_by"),
            filter_key=request.GET.get("filter"),
        )
        # P-20: the quality evaluation is read only once the results are open.
        evaluation = (
            None
            if results["locked"]
            else QualityService().evaluate_survey(request.user, survey_id)
        )
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("surveys:provider_dashboard")

    context = {
        "survey": _survey_row(survey),
        "locked": results["locked"],
        "response_count": results["response_count"],
        "min_responses": results["min_responses"],
    }
    if results["locked"]:
        # P-20: the service returned no results, so no chart data is built.
        context["results"] = {"survey_id": results["survey_id"]}
        return render(request, "analysis/analytics_dashboard.html", context)

    results_view = _results_view(results)
    context.update(
        {
            "results": results_view,
            "has_responses": results_view.get("response_count", 0) > 0,
            "open_text_question": any(
                summary["chart_type"] == "text"
                for summary in results_view["question_summaries"]
            ),
            "sentiment": _sentiment_panel(results),
            "group_by": results["group_by"] or "",
            "group_by_options": GROUP_BY_OPTIONS,
            "filter_options": results["filter_options"],
            "filter": results["filter"],
            "filter_unavailable": results["filter_unavailable"],
            "responses_over_time": [
                {"label": _day_label(row["date"]), "count": row["count"]}
                for row in results["responses_over_time"]
            ],
            "quality": None if evaluation["locked"] else _quality_panel(evaluation),
            "sentiment_chart_data": _sentiment_chart_data(results_view),
            "question_chart_data": _question_chart_data(
                results_view["question_summaries"],
            ),
        }
    )
    return render(request, "analysis/analytics_dashboard.html", context)


@require_POST
def retry_failed(request, survey_id):
    """Queue the survey's failed sentiment results again through AnalysisService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        count = AnalysisService().retry_failed(request.user, survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
    else:
        if count == 1:
            messages.success(request, "1 answer is queued for analysis again.")
        else:
            messages.success(request, f"{count} answers are queued for analysis again.")
    return redirect("analysis:analytics_dashboard", survey_id)


@require_http_methods(["GET", "POST"])
def exclude_flagged(request, survey_id):
    """GET confirms (board W-04); POST excludes the responses flagged and included now.

    The POST takes the flagged responses at that moment, so the count may differ from
    the page if responses arrived in between.
    """
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    service = QualityService()
    if request.method == "POST":
        try:
            count = service.exclude_flagged(request.user, survey_id)
        except SmartSurveyException as error:
            messages.error(request, str(error), extra_tags="danger")
        else:
            if count == 1:
                messages.success(
                    request,
                    "1 flagged response is excluded. You can include it again at any time.",
                )
            elif count > 1:
                messages.success(
                    request,
                    f"{count} flagged responses are excluded. "
                    "You can include them again at any time.",
                )
        return redirect("analysis:analytics_dashboard", survey_id)

    evaluation, response = _evaluation_or_redirect(request, service, survey_id)
    if response:
        return response
    count = evaluation["flagged_included_count"]
    if count == 0:
        return redirect("analysis:analytics_dashboard", survey_id)
    return render(
        request,
        "analysis/quality_confirm.html",
        {"action": "exclude", "survey_id": survey_id, "count": count},
    )


@require_http_methods(["GET", "POST"])
def include_all(request, survey_id):
    """GET confirms (board W-04); POST includes every excluded response of the survey."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    service = QualityService()
    if request.method == "POST":
        try:
            service.include_all(request.user, survey_id)
            total = service.evaluate_survey(request.user, survey_id)["response_count"]
        except SmartSurveyException as error:
            messages.error(request, str(error), extra_tags="danger")
        else:
            messages.success(request, f"All {total} responses are included.")
        return redirect("analysis:analytics_dashboard", survey_id)

    evaluation, response = _evaluation_or_redirect(request, service, survey_id)
    if response:
        return response
    total = evaluation["response_count"]
    excluded = total - evaluation["included_count"]
    if excluded == 0:
        return redirect("analysis:analytics_dashboard", survey_id)
    return render(
        request,
        "analysis/quality_confirm.html",
        {"action": "include", "survey_id": survey_id, "total": total, "excluded": excluded},
    )


def _evaluation_or_redirect(request, service, survey_id):
    """Return (open evaluation, None), or (None, redirect) on an error or a locked result."""
    try:
        evaluation = service.evaluate_survey(request.user, survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return None, redirect("surveys:provider_dashboard")
    if evaluation["locked"]:
        return None, redirect("analysis:analytics_dashboard", survey_id)
    return evaluation, None


def _quality_panel(evaluation):
    """Build the W-04 panel values from an open QualityService evaluation; the template writes the copy."""
    total = evaluation["response_count"]
    included = evaluation["included_count"]
    flag_counts = evaluation["flag_counts"]
    not_checked_counts = evaluation["not_checked_counts"]
    evaluated = total - evaluation["before_checks_count"]

    def not_checked_shown(code):
        if code not in QUALITY_NOT_CHECKED_CODES:
            return False
        if code == quality_rules.SPEEDING and (
            flag_counts[quality_rules.SIGNALS_MISSING] >= evaluated
        ):
            # Every evaluated response lacks its timings: the SIGNALS_MISSING row says why.
            return False
        return evaluated > 0 and flag_counts[code] == 0 and not_checked_counts[code] == evaluated

    flag_rows = [
        {"code": code, "count": flag_counts[code]}
        for code in QUALITY_FLAG_ORDER
        if flag_counts[code] > 0
    ]
    return {
        "rules_version": evaluation["rules_version"],
        "total": total,
        "included": included,
        "excluded": total - included,
        "before_checks": evaluation["before_checks_count"],
        "bands": evaluation["band_counts"],
        "flag_rows": flag_rows,
        "not_checked_rows": [code for code in QUALITY_FLAG_ORDER if not_checked_shown(code)],
        "flagged_included": evaluation["flagged_included_count"],
    }


def _sentiment_panel(results):
    """Build the W-05a panel counts from the open results of AnalysisService."""
    analysed = results["positive_count"] + results["neutral_count"] + results["negative_count"]
    waiting = results["waiting_count"]
    failed = results["failed_count"]
    return {
        "analysed": analysed,
        "waiting": waiting,
        "failed": failed,
        "skipped": results["skipped_count"],
        "total": analysed + waiting + failed,
        "failed_reasons": results["failed_reasons"],
        "analysis_overdue": results["analysis_overdue"],
    }


def _redirect_if_unauthenticated(request):
    """Return a login redirect when analytics access is unauthenticated."""
    if request.user.is_authenticated:
        return None

    messages.error(request, "Please log in to continue.", extra_tags="danger")
    return redirect("users:login")


def _survey_row(survey):
    """Build a template-ready survey summary for analytics."""
    return {
        "id": survey.survey_id,
        "title": survey.title,
        "description": survey.description,
        "is_closed": survey.status == SurveyStatus.CLOSED,
    }


def _results_view(results):
    """Build template-ready analytics data from AnalysisService output."""
    # Build a flat template-ready dict from the service output.
    # Counts come directly from the service; defaults are only applied
    # for keys that the service may legitimately omit (e.g. question_summaries).
    results_view = {
        "survey_id": results.get("survey_id"),
        "response_count": results.get("response_count", 0),
        "included_count": results.get("included_count", 0),
        "positive_count": results.get("positive_count", 0),
        "neutral_count": results.get("neutral_count", 0),
        "negative_count": results.get("negative_count", 0),
        "positive_rate": results.get("positive_rate", 0),
        "neutral_rate": results.get("neutral_rate", 0),
        "negative_rate": results.get("negative_rate", 0),
        "question_summaries": results.get("question_summaries", []),
    }

    # Preformat percentage labels for the template.
    results_view["positive_rate_label"] = _rate_label(results_view["positive_rate"])
    results_view["neutral_rate_label"] = _rate_label(results_view["neutral_rate"])
    results_view["negative_rate_label"] = _rate_label(results_view["negative_rate"])

    # Annotate each question summary with a chart element id and a type label.
    results_view["question_summaries"] = _question_summaries_view(
        results_view["question_summaries"],
    )
    return results_view


def _rate_label(rate):
    """Format an analytics rate as a percentage label."""
    return f"{rate * 100:.0f}%"


def _sentiment_chart_data(results):
    """Build sentiment chart data for the analytics dashboard."""
    return {
        "labels": ["Positive", "Neutral", "Negative"],
        "values": [
            results.get("positive_count", 0),
            results.get("neutral_count", 0),
            results.get("negative_count", 0),
        ],
    }


def _question_summaries_view(question_summaries):
    """Add chart element ids, type labels and the W-05b sentiment blocks to question summaries."""
    summaries = []
    for summary in question_summaries:
        view = {
            **summary,
            "chart_id": f"question-chart-{summary['question_id']}",
            "question_type_label": QUESTION_TYPE_LABELS[summary["question_type"]],
        }
        if "sentiment" in summary:
            view["sentiment_shares"] = _sentiment_shares(summary["sentiment"])
            view["breakdown_view"] = _breakdown_view(summary["breakdown"])
        if "group_table" in summary:
            view["group_table_view"] = _group_table_view(summary)
        summaries.append(view)
    return summaries


def _group_table_view(summary):
    """Build the FR-13 comparison table of one multiple-choice or rating question."""
    table = summary["group_table"]
    rows = []
    for row in table["rows"]:
        view_row = {**row}
        if "shares" in row:
            view_row["shares"] = [
                {**share, "label": _rate_label(share["share"])} for share in row["shares"]
            ]
        rows.append(view_row)
    return {
        "heading": GROUP_BY_HEADINGS[table["dimension"]],
        "enough": table["enough"],
        "options": summary["labels"] if summary["chart_type"] == "bar" else [],
        "rows": rows,
    }


def _day_label(day):
    """Format a date as "21 Nov" for the responses over time chart."""
    return f"{day.day} {day:%b}"


def _sentiment_shares(counts):
    """Return each sentiment's count, share label and whole-number bar width of the analysed.

    The labels round each share on its own, as the metric cards do. The widths use the
    largest remainder, so one bar's widths sum to 100 whenever an answer is analysed.
    """
    analysed = counts["analysed"]
    shares = []
    for key, name in SENTIMENT_NAMES:
        rate = counts[key] / analysed if analysed else 0
        shares.append(
            {
                "key": key,
                "name": name,
                "count": counts[key],
                "label": _rate_label(rate),
                "width": counts[key] * 100 // analysed if analysed else 0,
            }
        )
    if analysed:
        left = 100 - sum(share["width"] for share in shares)
        # sorted() is stable, so ties keep the order positive, neutral, negative.
        by_remainder = sorted(shares, key=lambda share: -(share["count"] * 100 % analysed))
        for share in by_remainder[:left]:
            share["width"] += 1
    return shares


def _breakdown_view(breakdown):
    """Build the W-05b group table of one open question, or None without a dimension."""
    if breakdown is None:
        return None
    return {
        "heading": GROUP_BY_HEADINGS[breakdown["dimension"]],
        "enough": breakdown["enough"],
        "rows": [
            {
                "label": row["label"],
                "analysed": row["analysed"],
                "pooled": row["pooled"],
                "shares": _sentiment_shares(row),
            }
            for row in breakdown["rows"]
        ],
    }


def _question_chart_data(question_summaries):
    """Build chart payloads for graphable question summaries."""
    return [
        {
            "chart_id": summary["chart_id"],
            "chart_type": summary["chart_type"],
            "labels": summary["labels"],
            "values": summary["values"],
        }
        for summary in question_summaries
        if summary["chart_type"] in {"bar", "rating"} and not summary["too_few"]
    ]
