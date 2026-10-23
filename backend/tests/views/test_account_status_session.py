import pytest
from django.urls import reverse

from apps.core.models import User
from core.enums import AccountStatus, UserType
from services.admin_service import AdminService


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["suspend_account", "delete_account"])
def test_suspended_or_deleted_user_loses_existing_session(client, action):
    admin = create_user(f"admin-{action}@example.com", UserType.ADMIN)
    respondent = create_user(f"respondent-{action}@example.com", UserType.RESPONDENT)
    client.force_login(respondent)
    dashboard_url = reverse("responses:respondent_dashboard")
    assert client.get(dashboard_url).status_code == 200

    getattr(AdminService(), action)(admin, respondent.user_id)
    response = client.get(dashboard_url)

    assert response.status_code == 302
    assert response.url.startswith(reverse("users:login"))


@pytest.mark.django_db
def test_reactivated_user_can_log_in_again(client):
    admin = create_user("admin-reactivate@example.com", UserType.ADMIN)
    respondent = create_user("respondent-reactivate@example.com", UserType.RESPONDENT)
    admin_service = AdminService()
    admin_service.suspend_account(admin, respondent.user_id)

    admin_service.activate_account(admin, respondent.user_id)
    client.force_login(User.objects.get(user_id=respondent.user_id))

    assert client.get(reverse("responses:respondent_dashboard")).status_code == 200
