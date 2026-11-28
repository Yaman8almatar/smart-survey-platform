from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("users/", views.user_management, name="user_management"),
    path("reports/", views.system_reports, name="system_reports"),
    path("reviews/", views.review_queue, name="review_queue"),
    path("reviews/<int:survey_id>/", views.review_survey, name="review_survey"),
    path(
        "reviews/<int:survey_id>/approve/",
        views.approve_survey,
        name="approve_survey",
    ),
    path(
        "reviews/<int:survey_id>/reject/",
        views.reject_survey,
        name="reject_survey",
    ),
]
