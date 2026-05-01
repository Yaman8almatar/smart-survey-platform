from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse

from core.enums import UserType
from core.exceptions import SmartSurveyException
from services.authentication_service import AuthenticationService

from .forms import (
    LoginForm,
    RespondentRegistrationForm,
    ServiceProviderRegistrationForm,
)


def home_redirect(request):
    """Render the public or role-specific home page after Authentication flow state."""
    if not request.user.is_authenticated:
        return render(
            request,
            "users/home.html",
            {"public_actions": _public_home_actions()},
        )

    user = request.user
    context = {
        "is_personal_home": True,
        "user_name": getattr(user, "name", "") or user.email,
        "user_email": user.email,
        "user_type": user.user_type,
        "account_status": user.account_status,
        "role_label": user.get_user_type_display(),
        "account_status_label": user.get_account_status_display(),
        "role_badge_class": _role_badge_class(user.user_type),
        "status_badge_class": _status_badge_class(user.account_status),
        "welcome_message": _welcome_message_for(user.user_type),
        "quick_actions": _quick_actions_for(user.user_type),
    }
    return render(request, "users/home.html", context)


def register_service_provider(request):
    """Render provider registration and delegate account creation to AuthenticationService."""
    if request.method == "POST":
        form = ServiceProviderRegistrationForm(request.POST)
        if form.is_valid():
            try:
                AuthenticationService().register_service_provider(
                    form.cleaned_data["name"],
                    form.cleaned_data["email"],
                    form.cleaned_data["password"],
                )
            except SmartSurveyException as error:
                messages.error(request, str(error), extra_tags="danger")
            else:
                messages.success(request, "Service provider account created.")
                return redirect("users:login")
    else:
        form = ServiceProviderRegistrationForm()

    return render(request, "users/register_service_provider.html", {"form": form})


def register_respondent(request):
    """Render respondent registration and delegate profile creation to AuthenticationService."""
    if request.method == "POST":
        form = RespondentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                AuthenticationService().register_respondent(
                    form.cleaned_data["name"],
                    form.cleaned_data["email"],
                    form.cleaned_data["password"],
                    form.cleaned_data["age"],
                    form.cleaned_data["gender"],
                    form.cleaned_data["region"],
                    form.cleaned_data["interests"],
                )
            except SmartSurveyException as error:
                messages.error(request, str(error), extra_tags="danger")
            else:
                messages.success(request, "Respondent account created.")
                return redirect("users:login")
    else:
        form = RespondentRegistrationForm()

    return render(request, "users/register_respondent.html", {"form": form})


def login_view(request):
    """Render login and delegate credential validation to AuthenticationService."""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                user = AuthenticationService().authenticate_user(
                    form.cleaned_data["email"],
                    form.cleaned_data["password"],
                )
            except SmartSurveyException as error:
                messages.error(request, str(error), extra_tags="danger")
            else:
                django_login(request, user)
                messages.success(request, "Logged in successfully.")
                return redirect(_dashboard_url_for(user))
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    """Render logout confirmation and end the active Django session."""
    if request.method == "POST":
        django_logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect("users:login")

    return render(request, "users/logout_confirm.html")


def _dashboard_url_for(user):
    """Return the dashboard URL for the authenticated user's role."""
    route_names = {
        UserType.SERVICE_PROVIDER: ["surveys:provider_dashboard"],
        UserType.RESPONDENT: ["responses:respondent_dashboard"],
        UserType.ADMIN: ["admin_panel:admin_dashboard"],
    }.get(user.user_type, [])

    for route_name in route_names:
        try:
            return reverse(route_name)
        except NoReverseMatch:
            continue

    return "/"


def _public_home_actions():
    """Build public home actions for unauthenticated visitors."""
    return _resolve_actions(
        [
            {
                "title": "Login",
                "description": "Access your account and continue your workflow.",
                "url_name": "users:login",
                "icon": "bi-box-arrow-in-right",
                "button_class": "btn-primary",
            },
            {
                "title": "Register Service Provider",
                "description": "Create surveys, manage questions, and review analytics.",
                "url_name": "users:register_service_provider",
                "icon": "bi-briefcase",
                "button_class": "btn-outline-primary",
            },
            {
                "title": "Register Respondent",
                "description": "Build your profile and participate in eligible surveys.",
                "url_name": "users:register_respondent",
                "icon": "bi-person-plus",
                "button_class": "btn-outline-secondary",
            },
        ]
    )


def _quick_actions_for(user_type):
    """Build role-specific quick actions for the home page."""
    actions_by_role = {
        UserType.SERVICE_PROVIDER: [
            {
                "title": "Provider Dashboard",
                "description": "Review provider activity and survey progress.",
                "url_name": "surveys:provider_dashboard",
                "icon": "bi-speedometer2",
            },
            {
                "title": "My Surveys",
                "description": "Open your survey list and manage current work.",
                "url_name": "surveys:survey_list",
                "icon": "bi-list-check",
            },
            {
                "title": "Create Survey",
                "description": "Start a new draft survey for your audience.",
                "url_name": "surveys:create_survey",
                "icon": "bi-plus-circle",
            },
        ],
        UserType.RESPONDENT: [
            {
                "title": "Respondent Dashboard",
                "description": "View your respondent workspace.",
                "url_name": "responses:respondent_dashboard",
                "icon": "bi-speedometer2",
            },
            {
                "title": "Demographic Profile",
                "description": "Keep eligibility information current.",
                "url_name": "responses:demographic_profile",
                "icon": "bi-person-vcard",
            },
            {
                "title": "Eligible Surveys",
                "description": "See surveys currently available to you.",
                "url_name": "responses:eligible_surveys",
                "icon": "bi-ui-checks-grid",
            },
            {
                "title": "Answered Surveys",
                "description": "Review surveys you have already submitted.",
                "url_name": "responses:answered_surveys",
                "icon": "bi-check2-square",
            },
        ],
        UserType.ADMIN: [
            {
                "title": "Admin Dashboard",
                "description": "Monitor platform administration at a glance.",
                "url_name": "admin_panel:admin_dashboard",
                "icon": "bi-speedometer2",
            },
            {
                "title": "User Management",
                "description": "Review and manage user account status.",
                "url_name": "admin_panel:user_management",
                "icon": "bi-people",
            },
            {
                "title": "System Reports",
                "description": "Open usage and activity reports.",
                "url_name": "admin_panel:system_reports",
                "icon": "bi-clipboard-data",
            },
        ],
    }
    return _resolve_actions(actions_by_role.get(user_type, []))


def _welcome_message_for(user_type):
    """Return the role-specific welcome message."""
    messages_by_role = {
        UserType.SERVICE_PROVIDER: "Manage surveys, questions, targeting criteria, and analytics.",
        UserType.RESPONDENT: (
            "Manage your profile and participate only in surveys you are eligible for."
        ),
        UserType.ADMIN: "Manage users and monitor system activity.",
    }
    return messages_by_role.get(user_type, "Use the navigation to continue.")


def _role_badge_class(user_type):
    """Return the Bootstrap badge class for a user role."""
    return {
        UserType.SERVICE_PROVIDER: "text-bg-primary",
        UserType.RESPONDENT: "text-bg-success",
        UserType.ADMIN: "text-bg-dark",
    }.get(user_type, "text-bg-secondary")


def _status_badge_class(account_status):
    """Return the Bootstrap badge class for an account status."""
    return {
        "ACTIVE": "text-bg-success",
        "SUSPENDED": "text-bg-warning",
        "DELETED": "text-bg-secondary",
    }.get(account_status, "text-bg-secondary")


def _resolve_actions(action_definitions):
    """Resolve URL names into displayable action links."""
    actions = []
    for action in action_definitions:
        try:
            url = reverse(action["url_name"])
        except NoReverseMatch:
            continue

        actions.append({**action, "url": url})

    return actions
