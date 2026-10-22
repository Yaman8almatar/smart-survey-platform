from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path(
        "register/service-provider/",
        views.register_service_provider,
        name="register_service_provider",
    ),
    path(
        "register/respondent/",
        views.register_respondent,
        name="register_respondent",
    ),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
