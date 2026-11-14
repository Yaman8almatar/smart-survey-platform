"""Home and admin user list: sentence-case account labels (TASK-24B, issue #61)."""

import pytest
from django.urls import reverse

from apps.core.models import User
from core.enums import AccountStatus, UserType


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.mark.django_db
def test_home_shows_sentence_case_account_labels_not_raw_values(client):
    provider = create_user("provider-home-labels@example.com", UserType.SERVICE_PROVIDER)
    client.force_login(provider)

    content = client.get(reverse("home")).content.decode()

    assert "Service provider" in content
    assert "Active" in content
    assert "Service Provider" not in content
    assert "SERVICE_PROVIDER" not in content
    assert "ACTIVE" not in content


@pytest.mark.django_db
def test_admin_user_list_shows_sentence_case_user_type(client):
    admin = create_user("admin-user-list-labels@example.com", UserType.ADMIN)
    create_user("provider-user-list-labels@example.com", UserType.SERVICE_PROVIDER)
    client.force_login(admin)

    content = client.get(reverse("admin_panel:user_management")).content.decode()

    assert "<td>Service provider</td>" in content
    assert "Service Provider" not in content
