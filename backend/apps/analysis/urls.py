from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    path(
        "surveys/<int:survey_id>/",
        views.analytics_dashboard,
        name="analytics_dashboard",
    ),
]
