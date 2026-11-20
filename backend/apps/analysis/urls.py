from django.urls import path

from . import export_views, response_views, views

app_name = "analysis"

urlpatterns = [
    path(
        "surveys/<int:survey_id>/",
        views.analytics_dashboard,
        name="analytics_dashboard",
    ),
    path(
        "surveys/<int:survey_id>/responses/",
        response_views.response_list,
        name="response_list",
    ),
    path(
        "surveys/<int:survey_id>/responses/export/csv/",
        export_views.response_export_csv,
        name="response_export_csv",
    ),
    path(
        "surveys/<int:survey_id>/responses/export/xlsx/",
        export_views.response_export_xlsx,
        name="response_export_xlsx",
    ),
    path(
        "surveys/<int:survey_id>/responses/<int:number>/",
        response_views.response_detail,
        name="response_detail",
    ),
    path(
        "surveys/<int:survey_id>/responses/<int:number>/inclusion/",
        response_views.response_inclusion,
        name="response_inclusion",
    ),
    path(
        "<int:survey_id>/retry-failed/",
        views.retry_failed,
        name="retry_failed",
    ),
    path(
        "<int:survey_id>/exclude-flagged/",
        views.exclude_flagged,
        name="exclude_flagged",
    ),
    path(
        "<int:survey_id>/include-all/",
        views.include_all,
        name="include_all",
    ),
]
