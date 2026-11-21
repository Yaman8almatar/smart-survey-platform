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
    path(
        "confirm-email/resend/",
        views.resend_confirmation,
        name="resend_confirmation",
    ),
    path(
        "confirm-email/<uidb64>/<token>/",
        views.confirm_email,
        name="confirm_email",
    ),
    path("password-reset/", views.password_reset, name="password_reset"),
    path(
        "password-reset/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
]
