from django.urls import path

from . import views

app_name = "surveys"

urlpatterns = [
    path("provider/dashboard/", views.provider_dashboard, name="provider_dashboard"),
    path("", views.survey_list, name="survey_list"),
    path("create/", views.create_survey, name="create_survey"),
    path("<int:survey_id>/edit/", views.edit_survey, name="edit_survey"),
    path(
        "<int:survey_id>/questions/",
        views.manage_questions,
        name="manage_questions",
    ),
    path(
        "<int:survey_id>/targeting/",
        views.targeting_criteria,
        name="targeting_criteria",
    ),
    path("<int:survey_id>/delete/", views.delete_survey, name="delete_survey"),
    path("<int:survey_id>/publish/", views.publish_survey, name="publish_survey"),
    path("<int:survey_id>/close/", views.close_survey, name="close_survey"),
]
