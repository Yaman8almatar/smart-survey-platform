from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.api.exceptions import CORE_ERRORS
from core.enums import (
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    SurveyStatus,
)
from core.exceptions import SmartSurveyException, ValidationError
from services.question_service import QuestionService
from services.survey_service import SurveyService
from services.targeting_service import TargetingService

from .forms import QuestionForm, SurveyForm, TargetingListsForm


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
                    shuffle_questions=form.cleaned_data["shuffle_questions"],
                    shuffle_options=form.cleaned_data["shuffle_options"],
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
                    shuffle_questions=form.cleaned_data["shuffle_questions"],
                    shuffle_options=form.cleaned_data["shuffle_options"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Survey updated successfully.")
                return redirect("surveys:survey_list")
    else:
        form = SurveyForm(
            initial={
                "title": survey.title,
                "description": survey.description,
                "shuffle_questions": survey.shuffle_questions,
                "shuffle_options": survey.shuffle_options,
            }
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
                    is_attention_check=form.cleaned_data["is_attention_check"],
                    expected_option_index=form.cleaned_data["expected_option"],
                    expected_rating=form.cleaned_data["expected_rating"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Question added successfully.")
                return redirect("surveys:manage_questions", survey_id)
    else:
        form = QuestionForm(initial={"order_index": 0, "is_required": True})

    questions = QuestionService().get_survey_question_rows(request.user, survey_id)
    attention_check_count = sum(1 for question in questions if question["is_attention_check"])
    context = {
        "survey": _survey_row(survey),
        "questions": questions,
        "form": form,
        "attention_check_count": attention_check_count,
        "attention_check_limit": QuestionService.MAX_ATTENTION_CHECKS,
        "attention_limit_reached": attention_check_count >= QuestionService.MAX_ATTENTION_CHECKS,
    }
    return render(request, "surveys/manage_questions.html", context)


@require_POST
def delete_question(request, survey_id, question_id):
    """Delete a draft-survey question through QuestionService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        QuestionService().delete_question(request.user, question_id)
    except SmartSurveyException as error:
        _show_service_error(request, error)
    else:
        messages.success(request, "Question deleted successfully.")
    return redirect("surveys:manage_questions", survey_id)


def targeting_criteria(request, survey_id):
    """Render the W-03 targeting page and delegate saving and the first reach to TargetingService.

    The first reach is rendered in the page (D-118); site.js then asks targeting_reach 400 ms
    after each change.
    """
    surveys, response = _load_provider_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(request, "Survey not found.", extra_tags="danger")
        return redirect("surveys:survey_list")

    service = TargetingService()
    if request.method == "POST":
        form = TargetingListsForm(request.POST)
        if form.is_valid():
            try:
                service.save_criteria(
                    request.user, survey_id, **_criteria_kwargs(form.cleaned_data)
                )
            except ValidationError as error:
                # The form checks each field; only the min-above-max rule reaches here.
                form.add_error("age_min", str(error))
            except SmartSurveyException as error:
                _show_service_error(request, error)
                return redirect("surveys:survey_list")
            else:
                messages.success(request, "Targeting criteria saved successfully.")
                return redirect("surveys:survey_list")
        reach = {"state": "invalid", "count": None, "total": None, "percent": None}
    else:
        try:
            initial = service.get_criteria_initial(request.user, survey_id)
            reach = service.reach(request.user, survey_id, **_criteria_kwargs(initial))
        except SmartSurveyException as error:
            _show_service_error(request, error)
            return redirect("surveys:survey_list")
        form = TargetingListsForm(
            initial={**initial, "gender": initial.get("gender") or Gender.ANY}
        )

    context = {
        "survey": _survey_row(survey),
        "form": form,
        "reach": _reach_card(reach),
        "who_summary": _who_summary(
            form["gender"].value(), form["age_min"].value(), form["age_max"].value()
        ),
        "age_phrases": AGE_PHRASES,
    }
    return render(request, "surveys/targeting_criteria.html", context)


@require_POST
def targeting_reach(request, survey_id):
    """Return the banded reach of the posted, unsaved criteria as JSON (W-03).

    Called by the targeting page while the provider edits; it never redirects, so every
    error is JSON {"error": code, "message"?}.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not_authenticated"}, status=401)

    form = TargetingListsForm(request.POST)
    if not form.is_valid():
        field, errors = next(iter(form.errors.items()))
        return JsonResponse(
            {"error": "validation_error", "message": f"{field}: {errors[0]}"},
            status=400,
        )

    try:
        reach = TargetingService().reach(
            request.user, survey_id, **_criteria_kwargs(form.cleaned_data)
        )
    except SmartSurveyException as error:
        status, code = _json_error(error)
        return JsonResponse({"error": code, "message": str(error)}, status=status)
    return JsonResponse(reach)


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


@require_http_methods(["GET", "POST"])
def publish_survey(request, survey_id):
    """GET shows the publish confirmation (W-03, P-19); POST publishes through SurveyService.

    The service stores reach_at_publish at the POST, which may differ from the number shown
    if profiles changed in between.
    """
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    service = SurveyService()
    if request.method == "POST":
        try:
            service.publish_survey(request.user, survey_id)
        except SmartSurveyException as error:
            _show_service_error(request, error)
        else:
            messages.success(request, "Survey published successfully.")
        return redirect("surveys:survey_list")

    try:
        # Raises what publishing would raise, so a survey that cannot be published never
        # reaches the page.
        preview = service.get_publish_preview(request.user, survey_id)
        survey = service.get_provider_survey(request.user, survey_id)
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return redirect("surveys:survey_list")

    criteria = preview["criteria"]
    context = {
        "survey": _survey_row(survey),
        "reach": _reach_card(preview["reach"]),
        "question_count": preview["question_count"],
        "who": {
            "gender": Gender(criteria["gender"]).label if criteria["gender"] else "",
            "age": _age_phrase(criteria["age_min"], criteria["age_max"]),
            "regions": _labels(Governorate, criteria["regions"]),
            "education_levels": _labels(Education, criteria["education_levels"]),
            "occupations": _labels(Occupation, criteria["occupations"]),
            "marital_statuses": _labels(MaritalStatus, criteria["marital_statuses"]),
            "interests": _labels(Interest, criteria["interests"]),
        },
    }
    return render(request, "surveys/publish_confirm.html", context)


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
        "can_edit": survey.can_edit(),
        "can_delete": survey.can_delete(),
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


def _criteria_kwargs(values):
    """Return TargetingService criteria keyword arguments from form data or saved values."""
    return {
        "gender": _blank_to_none(values.get("gender")),
        "age_min": values.get("age_min"),
        "age_max": values.get("age_max"),
        **{name: values.get(name) or [] for name, _, _ in TargetingService.LIST_CHOICES},
    }


# The age phrases of summaries; the targeting page hands the same formats to site.js.
AGE_PHRASES = {
    "both": "{min} to {max}",
    "min": "{min} or older",
    "max": "{max} or younger",
}


def _age_phrase(age_min, age_max):
    """Return "18 to 34", "18 or older", "34 or younger", or "" when both ages are empty."""
    has_min = age_min not in {None, ""}
    has_max = age_max not in {None, ""}
    if has_min and has_max:
        key = "both"
    elif has_min:
        key = "min"
    elif has_max:
        key = "max"
    else:
        return ""
    return AGE_PHRASES[key].format(min=age_min, max=age_max)


def _who_summary(gender, age_min, age_max):
    """Return the Who summary ("Female, 18 to 34"); "" means no restriction (shown as Any)."""
    parts = []
    if gender in {Gender.MALE, Gender.FEMALE}:
        parts.append(Gender(gender).label)
    phrase = _age_phrase(age_min, age_max)
    if phrase:
        parts.append(phrase)
    return ", ".join(parts)


def _labels(enum, values):
    """Return the enum labels of stored codes, in their stored order."""
    return [enum(value).label for value in values]


def _reach_card(reach):
    """Return reach values for the templates: count, total and percent only where shown.

    A hidden block never prints a number the visible state does not show (P-19).
    """
    shows_count = reach["state"] in {"everyone", "narrowed"}
    return {
        "state": reach["state"],
        "count": reach["count"] if shows_count else "",
        "total": reach["total"] if shows_count else "",
        "percent": (reach["percent"] or 0) if shows_count else 0,
    }


def _json_error(error):
    """Return (status, code) for a service error, from the API's shared mapping."""
    for exception_class, status_and_code in CORE_ERRORS.items():
        if isinstance(error, exception_class):
            return status_and_code
    return 500, "internal_error"


def _show_service_error(request, error):
    """Display a service-layer exception as a Django message."""
    messages.error(request, str(error), extra_tags="danger")
