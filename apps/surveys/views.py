from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.enums import SurveyStatus
from core.exceptions import SmartSurveyException
from services.question_service import QuestionService
from services.survey_service import SurveyService
from services.targeting_service import TargetingService

from .forms import QuestionForm, SurveyForm, TargetingCriteriaForm


def provider_dashboard(request):
    """Render provider dashboard data returned by SurveyService."""
    survey_items, response = _load_provider_survey_items_or_redirect(request)
    if response:
        return response

    surveys = [item["survey"] for item in survey_items]
    context = {
        "metrics": _dashboard_metrics(surveys),
        "recent_surveys": [_survey_item_row(item) for item in survey_items[:5]],
    }
    return render(request, "surveys/provider_dashboard.html", context)


def survey_list(request):
    """Render provider surveys and Survey status actions from SurveyService."""
    survey_items, response = _load_provider_survey_items_or_redirect(request)
    if response:
        return response

    context = {"surveys": [_survey_item_row(item) for item in survey_items]}
    return render(request, "surveys/survey_list.html", context)


def create_survey(request):
    """Render survey creation and delegate persistence to SurveyService."""
    _, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            try:
                survey = SurveyService().create_survey(
                    request.user,
                    form.cleaned_data["title"],
                    form.cleaned_data["description"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Survey created successfully.")
                return redirect("surveys:manage_questions", survey.survey_id)
    else:
        form = SurveyForm()

    return render(request, "surveys/create_survey.html", {"form": form})


def edit_survey(request, survey_id):
    """Render survey editing and delegate draft updates to SurveyService."""
    surveys, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(request, "Survey not found.", extra_tags="danger")
        return redirect("surveys:survey_list")

    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            try:
                SurveyService().update_survey(
                    request.user,
                    survey_id,
                    form.cleaned_data["title"],
                    form.cleaned_data["description"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Survey updated successfully.")
                return redirect("surveys:survey_list")
    else:
        form = SurveyForm(
            initial={"title": survey.title, "description": survey.description}
        )

    return render(
        request,
        "surveys/edit_survey.html",
        {"form": form, "survey": _survey_row(survey)},
    )


def manage_questions(request, survey_id):
    """Render Question management and delegate changes to QuestionService."""
    surveys, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(request, "Survey not found.", extra_tags="danger")
        return redirect("surveys:survey_list")

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            try:
                QuestionService().add_question_with_options(
                    request.user,
                    survey_id,
                    form.cleaned_data["question_text"],
                    form.cleaned_data["question_type"],
                    form.cleaned_data["is_required"],
                    form.cleaned_data["order_index"],
                    form.cleaned_data["options"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Question added successfully.")
                return redirect("surveys:manage_questions", survey_id)
    else:
        form = QuestionForm(initial={"order_index": 0, "is_required": True})

    context = {
        "survey": _survey_row(survey),
        "questions": QuestionService().get_survey_question_rows(request.user, survey_id),
        "form": form,
    }
    return render(request, "surveys/manage_questions.html", context)


def targeting_criteria(request, survey_id):
    """Render Targeting criteria and delegate changes to TargetingService."""
    surveys, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(request, "Survey not found.", extra_tags="danger")
        return redirect("surveys:survey_list")

    if request.method == "POST":
        form = TargetingCriteriaForm(request.POST)
        if form.is_valid():
            try:
                TargetingService().save_criteria(
                    request.user,
                    survey_id,
                    _blank_to_none(form.cleaned_data["gender"]),
                    form.cleaned_data["age_min"],
                    form.cleaned_data["age_max"],
                    _blank_to_none(form.cleaned_data["region"]),
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Targeting criteria saved successfully.")
                return redirect("surveys:survey_list")
    else:
        form = TargetingCriteriaForm(
            initial=TargetingService().get_criteria_initial(request.user, survey_id)
        )

    context = {"survey": _survey_row(survey), "form": form}
    return render(request, "surveys/targeting_criteria.html", context)


def delete_survey(request, survey_id):
    """Render survey deletion confirmation and delegate deletion to SurveyService."""
    surveys, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(request, "Survey not found.", extra_tags="danger")
        return redirect("surveys:survey_list")

    if request.method == "POST":
        try:
            SurveyService().delete_survey(request.user, survey_id)
        except SmartSurveyException as error:
            _show_service_error(request, error)
        else:
            messages.success(request, "Survey deleted successfully.")
            return redirect("surveys:survey_list")

    return render(
        request,
        "surveys/survey_confirm_delete.html",
        {"survey": _survey_row(survey)},
    )


@require_POST
def publish_survey(request, survey_id):
    """Handle publish Survey status action through SurveyService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        SurveyService().publish_survey(request.user, survey_id)
    except SmartSurveyException as error:
        _show_service_error(request, error)
    else:
        messages.success(request, "Survey published successfully.")
    return redirect("surveys:survey_list")


@require_POST
def close_survey(request, survey_id):
    """Handle close Survey status action through SurveyService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        SurveyService().close_survey(request.user, survey_id)
    except SmartSurveyException as error:
        _show_service_error(request, error)
    else:
        messages.success(request, "Survey closed successfully.")
    return redirect("surveys:survey_list")


def _load_provider_surveys_or_redirect(request):
    """Load provider surveys through SurveyService or return a redirect response."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return [], response

    try:
        surveys = list(SurveyService().list_provider_surveys(request.user))
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return [], redirect("users:login")

    return surveys, None


def _load_provider_survey_items_or_redirect(request):
    """Load provider survey rows with action flags through SurveyService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return [], response

    try:
        survey_items = list(SurveyService().list_provider_survey_items(request.user))
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return [], redirect("users:login")

    return survey_items, None


def _redirect_if_unauthenticated(request):
    """Return a login redirect when the user is not authenticated."""
    if request.user.is_authenticated:
        return None

    messages.error(request, "Please log in to continue.", extra_tags="danger")
    return redirect("users:login")


def _find_survey(surveys, survey_id):
    """Find a survey in an already authorized provider survey list."""
    for survey in surveys:
        if survey.survey_id == survey_id:
            return survey
    return None


def _dashboard_metrics(surveys):
    """Build provider dashboard counts grouped by survey status."""
    return {
        "total": len(surveys),
        "draft": _status_count(surveys, SurveyStatus.DRAFT),
        "published": _status_count(surveys, SurveyStatus.PUBLISHED),
        "closed": _status_count(surveys, SurveyStatus.CLOSED),
    }


def _status_count(surveys, status):
    """Count surveys matching a status."""
    return sum(1 for survey in surveys if survey.status == status)


def _survey_row(survey):
    """Build a template-ready survey row."""
    return {
        "id": survey.survey_id,
        "title": survey.title,
        "description": survey.description,
        "status": survey.status,
        "status_label": survey.get_status_display(),
        "status_badge": _status_badge(survey.status),
        "created_at": survey.created_at,
        "published_at": survey.published_at,
        "closed_at": survey.closed_at,
    }


def _survey_item_row(item):
    """Add service-provided action flags to a survey row."""
    row = _survey_row(item["survey"])
    row.update(
        {
            "can_edit": item["can_edit"],
            "can_delete": item["can_delete"],
            "can_publish": item["can_publish"],
            "can_close": item["can_close"],
            "can_manage_questions": item["can_manage_questions"],
            "can_manage_targeting": item["can_manage_targeting"],
            "can_view_analytics": item["can_view_analytics"],
        }
    )
    return row


def _status_badge(status):
    """Return the Bootstrap badge class for a survey status."""
    return {
        SurveyStatus.DRAFT: "text-bg-secondary",
        SurveyStatus.PUBLISHED: "text-bg-success",
        SurveyStatus.CLOSED: "text-bg-dark",
    }.get(status, "text-bg-secondary")


def _blank_to_none(value):
    """Normalize blank form values for service-layer criteria handling."""
    if value in {"", None}:
        return None
    return value


def _show_service_error(request, error):
    """Display a service-layer exception as a Django message."""
    messages.error(request, str(error), extra_tags="danger")
