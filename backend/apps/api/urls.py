from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/token/", views.TokenView.as_view(), name="token"),
    path("auth/token/refresh/", views.TokenRefresh.as_view(), name="token-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/profile/", views.ProfileView.as_view(), name="profile"),
    path("surveys/eligible/", views.EligibleSurveysView.as_view(), name="surveys-eligible"),
    path("surveys/<int:survey_id>/", views.SurveyDetailView.as_view(), name="survey-detail"),
    path(
        "surveys/<int:survey_id>/responses/",
        views.SubmitResponseView.as_view(),
        name="survey-submit",
    ),
    path("me/responses/", views.AnsweredSurveysView.as_view(), name="me-responses"),
]
