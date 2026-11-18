from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    path(
        "surveys/<int:survey_id>/",
        views.analytics_dashboard,
        name="analytics_dashboard",
    ),
    path(
        "<int:survey_id>/retry-failed/",
        views.retry_failed,
        name="retry_failed",
    ),
]
