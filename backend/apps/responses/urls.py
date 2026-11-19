from django.urls import path

from . import views

app_name = "responses"

# P-09: respondents answer in the app; the web keeps one page that sends them there.
urlpatterns = [
    path("", views.use_app, name="use_app"),
]
