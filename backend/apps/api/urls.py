from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/token/", views.TokenView.as_view(), name="token"),
    path("auth/token/refresh/", views.TokenRefresh.as_view(), name="token-refresh"),
]
