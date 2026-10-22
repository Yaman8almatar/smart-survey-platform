from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("users/", views.user_management, name="user_management"),
    path("reports/", views.system_reports, name="system_reports"),
]
