from django.urls import path

from . import views

app_name = "responses"

urlpatterns = [
    path(
        "respondent/dashboard/",
        views.respondent_dashboard,
        name="respondent_dashboard",
    ),
    path("profile/", views.demographic_profile, name="demographic_profile"),
    path("eligible-surveys/", views.eligible_surveys, name="eligible_surveys"),
    path("answered-surveys/", views.answered_surveys, name="answered_surveys"),
    path(
        "surveys/<int:survey_id>/submit/",
        views.submit_survey_response,
        name="submit_survey_response",
    ),
    path(
        "submission-confirmation/",
        views.submission_confirmation,
        name="submission_confirmation",
    ),
]
