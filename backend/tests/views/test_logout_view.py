import pytest
from django.urls import reverse

from apps.core.models import User
from core.enums import AccountStatus, UserType


@pytest.fixture
def logged_in_client(client):
    user = User.objects.create_user(
        email="logout-user@example.com",
        password="strong-password",
        name="Logout User",
        user_type=UserType.RESPONDENT,
        account_status=AccountStatus.ACTIVE,
    )
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_logout_get_is_rejected_and_keeps_session(logged_in_client):
    response = logged_in_client.get(reverse("users:logout"))

    assert response.status_code == 405
    assert "_auth_user_id" in logged_in_client.session


@pytest.mark.django_db
def test_logout_post_ends_session(logged_in_client):
    response = logged_in_client.post(reverse("users:logout"))

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert "_auth_user_id" not in logged_in_client.session


@pytest.mark.django_db
def test_navigation_logout_is_a_post_form(logged_in_client):
    response = logged_in_client.get(reverse("home"))
    content = response.content.decode()

    assert f'<form method="post" action="{reverse("users:logout")}"' in content
    assert f'href="{reverse("users:logout")}"' not in content
