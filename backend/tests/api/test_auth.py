import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.core.models import RespondentProfile, User
from core.enums import AccountStatus, UserType
from tests.api.conftest import PASSWORD

REGISTER_URL = "/api/v1/auth/register/"
TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"

pytestmark = pytest.mark.django_db


def registration_payload(**overrides):
    payload = {
        "name": "Sara",
        "email": "sara@example.com",
        "password": "a-strong-pass-1",
        "age": 28,
        "gender": "FEMALE",
        "region": "Aleppo",
        "interests": "reading",
    }
    payload.update(overrides)
    return payload


def test_register_creates_respondent_and_profile_without_tokens(client):
    response = client.post(REGISTER_URL, registration_payload(), format="json")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "name", "role"}
    assert body["email"] == "sara@example.com"
    assert body["role"] == UserType.RESPONDENT
    user = User.objects.get(email="sara@example.com")
    assert user.check_password("a-strong-pass-1")
    profile = RespondentProfile.objects.get(user=user)
    assert (profile.age, profile.gender, profile.region) == (28, "FEMALE", "Aleppo")


def test_register_rejects_duplicate_email(client, respondent):
    response = client.post(
        REGISTER_URL,
        registration_payload(email=respondent.email),
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Email is already registered.",
        }
    }


def test_register_reports_every_missing_field(client):
    response = client.post(REGISTER_URL, {}, format="json")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["fields"]) == {
        "name",
        "email",
        "password",
        "age",
        "gender",
        "region",
        "interests",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("age", 0),
        ("age", 121),
        ("age", "abc"),
        ("gender", "ANY"),
        ("gender", "OTHER"),
    ],
)
def test_register_rejects_invalid_field(client, field, value):
    response = client.post(
        REGISTER_URL,
        registration_payload(**{field: value}),
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert not User.objects.filter(email="sara@example.com").exists()


def test_register_then_token_flow(client):
    client.post(REGISTER_URL, registration_payload(), format="json")

    response = client.post(
        TOKEN_URL,
        {"email": "sara@example.com", "password": "a-strong-pass-1"},
        format="json",
    )

    assert response.status_code == 200


def test_token_returns_access_and_refresh(client, respondent):
    response = client.post(
        TOKEN_URL,
        {"email": respondent.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access", "refresh"}
    assert AccessToken(body["access"])["user_id"] == str(respondent.user_id)


def test_token_is_issued_to_other_roles_but_they_are_blocked_elsewhere(client, provider):
    response = client.post(
        TOKEN_URL,
        {"email": provider.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "respondent@example.com", "password": "wrong-password"},
        {"email": "nobody@example.com", "password": PASSWORD},
    ],
)
def test_token_rejects_bad_credentials(client, respondent, credentials):
    response = client.post(TOKEN_URL, credentials, format="json")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "access" not in response.json()


@pytest.mark.parametrize(
    "account_status",
    [AccountStatus.SUSPENDED, AccountStatus.DELETED],
)
def test_token_refuses_suspended_and_deleted_accounts(
    client, make_respondent, account_status
):
    user = make_respondent(email="gone@example.com", account_status=account_status)

    response = client.post(
        TOKEN_URL,
        {"email": user.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_token_refuses_account_marked_suspended_but_still_active_flag(
    client, respondent
):
    # Rows suspended before F-18 kept is_active=True; the service rule must still apply.
    User.objects.filter(pk=respondent.pk).update(
        account_status=AccountStatus.SUSPENDED
    )

    response = client.post(
        TOKEN_URL,
        {"email": respondent.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 401


def test_token_requires_email_and_password(client):
    response = client.post(TOKEN_URL, {}, format="json")

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"email", "password"}


def test_refresh_returns_new_access_token(client, respondent):
    refresh = RefreshToken.for_user(respondent)

    response = client.post(REFRESH_URL, {"refresh": str(refresh)}, format="json")

    assert response.status_code == 200
    assert AccessToken(response.json()["access"])["user_id"] == str(respondent.user_id)


def test_refresh_rejects_invalid_token(client):
    response = client.post(REFRESH_URL, {"refresh": "not-a-token"}, format="json")

    assert response.status_code == 401
    assert set(response.json()) == {"error"}


def test_refresh_requires_refresh_field(client):
    response = client.post(REFRESH_URL, {}, format="json")

    assert response.status_code == 400
    assert "refresh" in response.json()["error"]["fields"]


def test_refresh_refuses_account_suspended_after_token_issue(client, respondent):
    refresh = RefreshToken.for_user(respondent)
    User.objects.filter(pk=respondent.pk).update(
        account_status=AccountStatus.SUSPENDED, is_active=False
    )

    response = client.post(REFRESH_URL, {"refresh": str(refresh)}, format="json")

    assert response.status_code == 401
