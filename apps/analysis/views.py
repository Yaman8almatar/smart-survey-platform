from django.contrib import messages
from django.shortcuts import redirect, render

from core.exceptions import SmartSurveyException
from services.analysis_service import AnalysisService
from services.survey_service import SurveyService


def analytics_dashboard(request, survey_id):
    """Render provider survey analytics using SurveyService and AnalysisService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        survey = SurveyService().get_provider_survey(request.user, survey_id)
        results = AnalysisService().get_survey_results(survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("surveys:provider_dashboard")

    results_view = _results_view(results)
    context = {
        "survey": _survey_row(survey),
        "results": results_view,
        "has_responses": results_view.get("response_count", 0) > 0,
        "sentiment_chart_data": _sentiment_chart_data(results_view),
        "question_chart_data": _question_chart_data(
            results_view["question_summaries"],
        ),
    }
    return render(request, "analysis/analytics_dashboard.html", context)


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
    }


def _results_view(results):
    """Build template-ready analytics data from AnalysisService output."""
    # Build a flat template-ready dict from the service output.
    # Counts come directly from the service; defaults are only applied
    # for keys that the service may legitimately omit (e.g. question_summaries).
    results_view = {
        "survey_id": results.get("survey_id"),
        "response_count": results.get("response_count", 0),
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

    # Annotate each question summary with a unique chart element id.
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
    """Add chart element ids to question-level analytics summaries."""
    return [
        {
            **summary,
            "chart_id": f"question-chart-{summary['question_id']}",
        }
        for summary in question_summaries
    ]


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
        if summary["chart_type"] in {"bar", "rating"}
    ]
