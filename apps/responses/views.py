from django.contrib import messages
from django.shortcuts import redirect, render

from core.enums import SurveyStatus
from core.exceptions import SmartSurveyException
from services.profile_service import ProfileService
from services.question_service import QuestionService
from services.response_service import ResponseService
from services.survey_service import SurveyService

from .forms import DemographicProfileForm


def respondent_dashboard(request):
    """Render respondent dashboard using ProfileService and SurveyService data."""
    profile, surveys, response = _load_respondent_context_or_redirect(request)
    if response:
        return response

    context = {
        "profile_complete": bool(profile and profile.is_complete()),
        "eligible_surveys_count": len(surveys),
    }
    return render(request, "responses/respondent_dashboard.html", context)


def demographic_profile(request):
    """Render Profile management and delegate updates to ProfileService."""
    profile, _, response = _load_respondent_context_or_redirect(request)
    if response:
        return response

    if request.method == "POST":
        form = DemographicProfileForm(request.POST)
        if form.is_valid():
            try:
                ProfileService().update_profile(
                    request.user,
                    form.cleaned_data["age"],
                    form.cleaned_data["gender"],
                    form.cleaned_data["region"],
                    form.cleaned_data["interests"],
                )
            except SmartSurveyException as error:
                _show_service_error(request, error)
            else:
                messages.success(request, "Demographic profile saved successfully.")
                return redirect("responses:respondent_dashboard")
    else:
        form = DemographicProfileForm(initial=_profile_initial(profile))

    return render(request, "responses/demographic_profile.html", {"form": form})


def eligible_surveys(request):
    """Render eligible surveys returned by SurveyService filtering."""
    surveys, response = _load_eligible_surveys_or_redirect(request)
    if response:
        return response

    context = {"surveys": [_survey_row(survey) for survey in surveys]}
    return render(request, "responses/eligible_surveys.html", context)


def answered_surveys(request):
    """Render Answered surveys returned by ResponseService."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response

    try:
        surveys = ResponseService().get_answered_surveys(request.user)
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return redirect("users:login")

    return render(
        request,
        "responses/answered_surveys.html",
        {"surveys": surveys},
    )


def submit_survey_response(request, survey_id):
    """Render and process respondent survey submission through ResponseService."""
    surveys, response = _load_eligible_surveys_or_redirect(request)
    if response:
        return response

    survey = _find_survey(surveys, survey_id)
    if survey is None:
        messages.error(
            request,
            "This survey is not currently available for your account.",
            extra_tags="danger",
        )
        return redirect("responses:eligible_surveys")

    questions = QuestionService().get_response_form_questions(survey_id)

    if request.method == "POST":
        try:
            ResponseService().submit_response(
                request.user,
                survey_id,
                _collect_answers(request.POST, questions),
            )
        except SmartSurveyException as error:
            _show_service_error(request, error)
        else:
            messages.success(request, "Survey response submitted successfully.")
            return redirect("responses:submission_confirmation")

    context = {"survey": _survey_row(survey), "questions": questions}
    return render(request, "responses/submit_survey_response.html", context)


def submission_confirmation(request):
    """Render confirmation after successful Response submission."""
    _, _, response = _load_respondent_context_or_redirect(request)
    if response:
        return response

    return render(request, "responses/submission_confirmation.html")


def _load_respondent_context_or_redirect(request):
    """Load respondent profile and eligible surveys through services."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return None, [], response

    try:
        profile = ProfileService().get_profile(request.user)
        surveys = list(SurveyService().get_eligible_surveys(request.user))
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return None, [], redirect("users:login")

    return profile, surveys, None


def _load_eligible_surveys_or_redirect(request):
    """Load eligible surveys through SurveyService or return a redirect."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return [], response

    try:
        surveys = list(SurveyService().get_eligible_surveys(request.user))
    except SmartSurveyException as error:
        _show_service_error(request, error)
        return [], redirect("users:login")

    return surveys, None


def _redirect_if_unauthenticated(request):
    """Return a login redirect when the user is not authenticated."""
    if request.user.is_authenticated:
        return None

    messages.error(request, "Please log in to continue.", extra_tags="danger")
    return redirect("users:login")


def _profile_initial(profile):
    """Build initial form values from a respondent profile."""
    if profile is None:
        return {}

    return {
        "age": profile.age,
        "gender": profile.gender,
        "region": profile.region,
        "interests": profile.interests,
    }


def _survey_row(survey):
    """Build a template-ready eligible survey row."""
    return {
        "id": survey.survey_id,
        "title": survey.title,
        "description": survey.description,
        "status": survey.status,
        "status_label": survey.get_status_display(),
        "status_badge": _status_badge(survey.status),
    }


def _status_badge(status):
    """Return the Bootstrap badge class for a survey status."""
    return {
        SurveyStatus.DRAFT: "text-bg-secondary",
        SurveyStatus.PUBLISHED: "text-bg-success",
        SurveyStatus.CLOSED: "text-bg-dark",
    }.get(status, "text-bg-secondary")


def _find_survey(surveys, survey_id):
    """Find a survey in the service-filtered eligible survey list."""
    for survey in surveys:
        if survey.survey_id == survey_id:
            return survey
    return None


def _collect_answers(post_data, questions):
    """Collect submitted answer values using service-generated field names."""
    return [
        {
            "question_id": question["question_id"],
            "answer_value": _blank_to_none(post_data.get(question["answer_name"])),
            "rating_value": _optional_int(post_data.get(question["rating_name"])),
            "selected_option_id": _optional_int(post_data.get(question["option_name"])),
        }
        for question in questions
    ]


def _blank_to_none(value):
    """Normalize blank text values to None."""
    if value is None or value.strip() == "":
        return None
    return value


def _optional_int(value):
    """Convert optional numeric form values to integers when possible."""
    if value in {None, ""}:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _show_service_error(request, error):
    """Display a service-layer exception as a Django message."""
    messages.error(request, str(error), extra_tags="danger")
