from django.contrib import messages
from django.shortcuts import redirect, render

from apps.users.views import _dashboard_url_for
from core.enums import UserType


def use_app(request):
    """Tell a signed-in respondent to answer surveys in the app (P-09)."""
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to continue.", extra_tags="danger")
        return redirect("users:login")

    if request.user.user_type != UserType.RESPONDENT:
        return redirect(_dashboard_url_for(request.user))

    return render(request, "responses/use_app.html")
