import pytest
from django.core import mail

from apps.core.models import User

REGISTER_URL = "/api/v1/auth/register/"
TOKEN_URL = "/api/v1/auth/token/"
NOT_CONFIRMED = "Confirm your email address first. Open the link we sent you, or send a new one."

pytestmark = pytest.mark.django_db


def registration_payload():
    return {
        "name": "Sara",
        "email": "sara@example.com",
        "password": "a-strong-pass-1",
        "age": 28,
        "gender": "FEMALE",
        "region": "ALEPPO",
        "interests": ["EDUCATION"],
    }


def test_registration_sends_one_confirmation_email(client):
    response = client.post(REGISTER_URL, registration_payload(), format="json")

    assert response.status_code == 201
    assert set(response.json()) == {"id", "email", "name", "role"}
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["sara@example.com"]
    assert message.subject == "Confirm your Smart Survey email address"
    assert "http://testserver/users/confirm-email/" in message.body
    assert User.objects.get(email="sara@example.com").email_verified is False


def test_a_failed_registration_sends_no_email(client, respondent):
    payload = registration_payload()
    payload["email"] = respondent.email

    response = client.post(REGISTER_URL, payload, format="json")

    assert response.status_code == 400
    assert mail.outbox == []


def test_unconfirmed_account_gets_403_email_not_confirmed(client):
    client.post(REGISTER_URL, registration_payload(), format="json")

    response = client.post(
        TOKEN_URL,
        {"email": "sara@example.com", "password": "a-strong-pass-1"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "email_not_confirmed", "message": NOT_CONFIRMED}
    }


def test_unconfirmed_account_with_a_wrong_password_still_gets_401(client):
    client.post(REGISTER_URL, registration_payload(), format="json")

    response = client.post(
        TOKEN_URL,
        {"email": "sara@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_accounts_made_by_create_user_get_tokens(client, respondent):
    response = client.post(
        TOKEN_URL,
        {"email": respondent.email, "password": "strong-password"},
        format="json",
    )

    assert response.status_code == 200
