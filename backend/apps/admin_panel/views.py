from datetime import date, timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.surveys.views import publish_summary_context
from core.enums import USER_TYPE_LABELS, AccountStatus, UserType
from core.exceptions import SmartSurveyException, ValidationError
from services.admin_service import AdminService
from services.survey_review_service import SurveyReviewService


def admin_dashboard(request):
    """Render administrator quick actions after role validation."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    pending_count = SurveyReviewService().count_pending(request.user)
    return render(
        request,
        "admin_panel/admin_dashboard.html",
        {"pending_count": pending_count},
    )


def review_queue(request):
    """Render the surveys waiting for review, oldest first (FR-12)."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    try:
        rows = SurveyReviewService().list_pending(request.user)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        rows = []
    return render(request, "admin_panel/review_queue.html", {"rows": rows})


def review_survey(request, survey_id):
    """Render one pending survey with its targeting and questions for the admin's decision."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    try:
        review = SurveyReviewService().get_review(request.user, survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return redirect("admin_panel:review_queue")

    context = {
        "survey": review["survey"],
        "provider_name": review["provider_name"],
        "provider_email": review["provider_email"],
        "submitted_at": review["submitted_at"],
        "questions": review["questions"],
        **publish_summary_context(review["criteria"], review["reach"]),
    }
    return render(request, "admin_panel/review_survey.html", context)


@require_POST
def approve_survey(request, survey_id):
    """Approve a pending survey; it is published at once."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    try:
        SurveyReviewService().approve(request.user, survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
    else:
        messages.success(request, "Survey approved and published.")
    return redirect("admin_panel:review_queue")


@require_POST
def reject_survey(request, survey_id):
    """Return a pending survey to its provider with the admin's reason."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    try:
        SurveyReviewService().reject(request.user, survey_id, request.POST.get("reason", ""))
    except ValidationError as error:
        # A reason error keeps the admin on the review page to write it again.
        messages.error(request, str(error), extra_tags="danger")
        return redirect("admin_panel:review_survey", survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
    else:
        messages.success(request, "Survey returned to the provider.")
    return redirect("admin_panel:review_queue")


def user_management(request):
    """Render administrator account management using AdminService action flags."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    admin_service = AdminService()

    if request.method == "POST":
        _process_account_action(request)
        return redirect("admin_panel:user_management")

    try:
        users = _user_rows(admin_service.list_user_management_items(request.user))
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        users = []

    return render(
        request,
        "admin_panel/user_management.html",
        {"users": users},
    )


def _process_account_action(request):
    """Parse and run an administrator account action."""
    action = request.POST.get("action")
    user_id = request.POST.get("user_id")

    try:
        user_id = int(user_id)
        _run_account_action(request.user, user_id, action)
    except (TypeError, ValueError):
        messages.error(request, "Invalid account selection.", extra_tags="danger")
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
    else:
        messages.success(request, "Account updated successfully.")


def system_reports(request):
    """Render administrator system reports using AdminService metrics."""
    response = _redirect_if_not_admin(request)
    if response:
        return response

    report = None
    date_from = request.POST.get("date_from") or request.GET.get("date_from")
    date_to = request.POST.get("date_to") or request.GET.get("date_to")

    try:
        date_from_value, date_to_value = _report_date_range(date_from, date_to)
        if date_from_value is not None:
            date_from = date_from or date_from_value.isoformat()
        if date_to_value is not None:
            date_to = date_to or date_to_value.isoformat()
        report = AdminService().generate_system_report(
            request.user,
            date_from_value,
            date_to_value,
        )
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid date range.", extra_tags="danger")
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")

    context = {
        "report": report,
        "date_from": date_from or "",
        "date_to": date_to or "",
    }
    return render(request, "admin_panel/system_reports.html", context)


def _redirect_if_not_admin(request):
    """Return a redirect when the current user is not an administrator."""
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to continue.", extra_tags="danger")
        return redirect("users:login")

    if request.user.user_type != UserType.ADMIN:
        messages.error(request, "Access denied.", extra_tags="danger")
        return redirect("users:login")

    return None


def _user_rows(items):
    """Build template-ready rows for admin account management."""
    return [
        _user_row(item)
        for item in items
    ]


def _user_row(item):
    """Build one admin account management row."""
    user = item["user"]
    return {
        "user": user,
        "is_self": item["is_self"],
        "can_activate": item["can_activate"],
        "can_suspend": item["can_suspend"],
        "can_delete": item["can_delete"],
        "id": user.user_id,
        "name": user.name,
        "email": user.email,
        "user_type_label": USER_TYPE_LABELS[user.user_type],
        "account_status": user.account_status,
        "account_status_label": user.get_account_status_display(),
        "status_badge": _status_badge(user.account_status),
        "created_at": user.created_at,
    }


def _status_badge(status):
    """Return the Bootstrap badge class for an account status."""
    return {
        AccountStatus.ACTIVE: "text-bg-success",
        AccountStatus.SUSPENDED: "text-bg-warning",
        AccountStatus.DELETED: "text-bg-dark",
    }.get(status, "text-bg-secondary")


def _run_account_action(admin_user, user_id, action):
    """Dispatch an administrator account action to AdminService."""
    admin_service = AdminService()

    if action == "activate":
        return admin_service.activate_account(admin_user, user_id)
    if action == "suspend":
        return admin_service.suspend_account(admin_user, user_id)
    if action == "delete":
        return admin_service.delete_account(admin_user, user_id)

    raise ValueError("Unsupported account action.")


def _parse_date(value):
    """Parse an optional ISO date value from report filters."""
    if not value:
        return None

    return date.fromisoformat(value)


def _report_date_range(date_from, date_to):
    """Return the requested or default system report date range."""
    if not date_from and not date_to:
        date_to_value = date.today()
        return date_to_value - timedelta(days=30), date_to_value

    return _parse_date(date_from), _parse_date(date_to)
