"""FR-07 and FR-09 (board W-07): the survey's responses one by one, each under a number."""

from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.enums import QuestionType
from core.exceptions import (
    ResponseNotFound,
    SmartSurveyException,
    SurveyNotFound,
    UnauthorizedAction,
)
from services import quality_rules
from services.quality_service import QualityService
from services.response_review_service import ResponseReviewService
from services.response_service import ResponseService
from services.survey_service import SurveyService

from .views import QUALITY_FLAG_ORDER, _redirect_if_unauthenticated, _survey_row

PAGE_SIZE = 25
MAX_RATING = ResponseService.MAX_RATING

# The W-04 panel's flag names and meanings (D-188), shown in QUALITY_FLAG_ORDER.
FLAG_NAMES = {
    quality_rules.ATTENTION_FAILED: "Failed attention check",
    quality_rules.SPEEDING: "Answered very fast",
    quality_rules.DUPLICATE_DEVICE: "Same device as another account",
    quality_rules.STRAIGHT_LINING: "Same rating on every rating question",
    quality_rules.SIGNALS_MISSING: "Timing or device data missing",
}
FLAG_MEANINGS = {
    quality_rules.ATTENTION_FAILED: "Chose a different answer than the attention check asked for.",
    quality_rules.SPEEDING: (
        "Half or more of the closed questions took under 2 seconds, "
        "or the whole response was twice as fast as most."
    ),
    quality_rules.DUPLICATE_DEVICE: (
        "Two accounts answered from one app installation. Both responses are flagged."
    ),
    quality_rules.STRAIGHT_LINING: "All 5 or more rating answers are identical.",
    quality_rules.SIGNALS_MISSING: (
        "The app sent no timings or device ID, or its times exceed the server's clock."
    ),
}
BAND_NAMES = {
    quality_rules.CLEAN: "Clean",
    quality_rules.CHECK: "Check",
    quality_rules.LOW: "Low",
}
SENTIMENT_NAMES = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
    "waiting": "Waiting for analysis",
    "failed": "Could not be analysed",
}
# Never one for DUPLICATE_DEVICE: a missing device ID already shows SIGNALS_MISSING.
NOT_CHECKED_REASONS = {
    quality_rules.ATTENTION_FAILED: "This survey has no attention check.",
    quality_rules.SPEEDING: "Needs at least 3 answered closed questions.",
    quality_rules.STRAIGHT_LINING: "Needs 5 or more rating questions.",
}
SHOW_OPTIONS = (
    ("all", "All responses"),
    ("included", "Included"),
    ("excluded", "Excluded"),
    ("flagged", "Flagged"),
)
ORDER_OPTIONS = (
    ("score", "Lowest score first"),
    ("newest", "Newest first"),
    ("oldest", "Oldest first"),
)
BEFORE_CHECKS_NOTE = (
    "This response was collected before quality checks. It has no score and stays included."
)


def response_list(request, survey_id):
    """Render the numbered responses of a survey with a filter, an order and pages."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        survey = SurveyService().get_provider_survey(request.user, survey_id)
        result = ResponseReviewService().list_responses(
            request.user,
            survey_id,
            show=request.GET.get("show"),
            order=request.GET.get("order"),
        )
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("surveys:provider_dashboard")

    context = {"survey": _survey_row(survey), "locked": result["locked"]}
    if result["locked"]:
        context.update(
            {"response_count": result["response_count"], "min_responses": result["min_responses"]}
        )
        return render(request, "analysis/response_list.html", context)

    page = Paginator(result["rows"], PAGE_SIZE).get_page(request.GET.get("page"))
    list_url = reverse("analysis:response_list", args=[survey_id])

    def page_url(number):
        query = urlencode({"show": result["show"], "order": result["order"], "page": number})
        return f"{list_url}?{query}"

    context.update(
        {
            "total": result["total"],
            "included": result["included"],
            "excluded": result["excluded"],
            "show": result["show"],
            "order": result["order"],
            "show_options": SHOW_OPTIONS,
            "order_options": ORDER_OPTIONS,
            "page": page,
            "rows": [_list_row(row) for row in page.object_list],
            "previous_url": page_url(page.previous_page_number()) if page.has_previous() else None,
            "next_url": page_url(page.next_page_number()) if page.has_next() else None,
        }
    )
    return render(request, "analysis/response_list.html", context)


def response_detail(request, survey_id, number):
    """Render one response by its number: its answers, its quality verdict and its inclusion."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        survey = SurveyService().get_provider_survey(request.user, survey_id)
        result = ResponseReviewService().get_response(request.user, survey_id, number)
    except ResponseNotFound as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("analysis:response_list", survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("surveys:provider_dashboard")

    context = {"survey": _survey_row(survey), "locked": result["locked"]}
    if result["locked"]:
        context.update(
            {"response_count": result["response_count"], "min_responses": result["min_responses"]}
        )
        return render(request, "analysis/response_detail.html", context)

    before_checks = result["status"] == quality_rules.BEFORE_CHECKS
    flags = set(result["flags"])
    context.update(
        {
            "number": result["number"],
            "total": result["total"],
            "submitted_at": result["submitted_at"],
            "active_time": None if before_checks else _active_time(result["active_ms"]),
            "is_excluded": result["is_excluded"],
            "before_checks": before_checks,
            "before_checks_note": BEFORE_CHECKS_NOTE,
            "score": result["score"],
            "band_key": (result["band"] or "").lower(),
            "band_name": BAND_NAMES.get(result["band"]),
            "flags": [
                {"name": FLAG_NAMES[code], "meaning": FLAG_MEANINGS[code]}
                for code in QUALITY_FLAG_ORDER
                if code in flags
            ],
            "not_checked_lines": _not_checked_lines(result["not_checked"], flags),
            "can_change_inclusion": result["is_excluded"] or not before_checks,
            "previous_number": result["previous_number"],
            "next_number": result["next_number"],
            "answers": [_answer_view(answer) for answer in result["answers"]],
        }
    )
    return render(request, "analysis/response_detail.html", context)


@require_POST
def response_inclusion(request, survey_id, number):
    """Exclude or include one response by its number, then return to its page."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    action = request.POST.get("action")
    if action not in ("exclude", "include"):
        return HttpResponseBadRequest("Unknown action.")

    try:
        count = QualityService().set_response_inclusion(
            request.user, survey_id, number, action == "exclude"
        )
    except ResponseNotFound as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("analysis:response_list", survey_id)
    except (UnauthorizedAction, SurveyNotFound) as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("surveys:provider_dashboard")
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
    else:
        if count and action == "exclude":
            messages.success(
                request,
                f"Response {number} is excluded. You can include it again at any time.",
            )
        elif count:
            messages.success(request, f"Response {number} is included again.")
    return redirect("analysis:response_detail", survey_id, number)


def _list_row(row):
    """Return the display texts of one list row."""
    before_checks = row["status"] == quality_rules.BEFORE_CHECKS
    if before_checks:
        score, flags = "Before quality checks", "Not checked"
    else:
        score = f"{row['score']} · {BAND_NAMES[row['band']]}"
        names = [FLAG_NAMES[code] for code in QUALITY_FLAG_ORDER if code in row["flags"]]
        flags = ", ".join(names) if names else "No flag"
    return {
        "number": row["number"],
        "submitted_at": row["submitted_at"],
        "score": score,
        "flags": flags,
        "open_answers": _open_answers_text(row["open_answers"]),
        "is_excluded": row["is_excluded"],
    }


def _open_answers_text(counts):
    """Return the "Open answers" cell of one row."""
    if counts["waiting"] > 0:
        return SENTIMENT_NAMES["waiting"]
    analysed = [
        f"{counts[key]} {key}" for key in ("positive", "neutral", "negative") if counts[key] > 0
    ]
    if analysed:
        return ", ".join(analysed)
    if counts["failed"] > 0:
        return SENTIMENT_NAMES["failed"]
    return "No open answer"


def _active_time(active_ms):
    """Return the active time in whole seconds, as "S s" or "M min S s", or None."""
    if active_ms is None:
        return None
    seconds = active_ms // 1000
    if seconds < 60:
        return f"{seconds} s"
    return f"{seconds // 60} min {seconds % 60} s"


def _not_checked_lines(not_checked, flags):
    """Return the "Not checked" lines of one response, by the W-04 panel's rule."""
    lines = []
    for code in QUALITY_FLAG_ORDER:
        if code not in not_checked or code not in NOT_CHECKED_REASONS:
            continue
        if code == quality_rules.SPEEDING and quality_rules.SIGNALS_MISSING in flags:
            # Missing timings already show "Timing or device data missing".
            continue
        lines.append(f"Not checked: {FLAG_NAMES[code]}. {NOT_CHECKED_REASONS[code]}")
    return lines


def _display(question_type, value):
    """Return an answer or expected value as shown: the option text, "N of 5", or the text."""
    if value is None:
        return None
    if question_type == QuestionType.RATING_SCALE:
        return f"{value} of {MAX_RATING}"
    return value


def _answer_view(answer):
    """Return the display values of one answer item."""
    return {
        "position": answer["position"],
        "question_text": answer["question_text"],
        "answered": answer["answered"],
        "display": _display(answer["question_type"], answer["value"]),
        "is_attention_check": answer["is_attention_check"],
        "expected": _display(answer["question_type"], answer["expected"]),
        "sentiment": SENTIMENT_NAMES.get(answer["sentiment"]),
    }
