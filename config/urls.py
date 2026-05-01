from django.contrib import admin
from django.urls import include, path

from apps.users import views as user_views


urlpatterns = [
    path("", user_views.home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("admin-panel/", include("apps.admin_panel.urls")),
    path("analysis/", include("apps.analysis.urls")),
    path("responses/", include("apps.responses.urls")),
    path("surveys/", include("apps.surveys.urls")),
    path("users/", include("apps.users.urls")),
]
