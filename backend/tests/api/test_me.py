from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import RespondentProfile
from core.enums import UserType

ME_URL = "/api/v1/me/"
PROFILE_URL = "/api/v1/me/profile/"

pytestmark = pytest.mark.django_db


def test_me_returns_account_data(client, authenticate, respondent):
    authenticate(respondent)

    response = client.get(ME_URL)

    assert response.status_code == 200
    assert response.json() == {
        "id": respondent.user_id,
        "email": "respondent@example.com",
        "name": "Test User",
        "role": UserType.RESPONDENT,
    }


def test_me_rejects_expired_access_token(client, respondent):
    token = AccessToken.for_user(respondent)
    token.set_exp(lifetime=-timedelta(minutes=1))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get(ME_URL)

    assert response.status_code == 401
    assert set(response.json()) == {"error"}


def test_profile_get_returns_demographics(client, authenticate, respondent):
    authenticate(respondent)

    response = client.get(PROFILE_URL)

    assert response.status_code == 200
    assert response.json() == {
        "age": 30,
        "gender": "MALE",
        "region": "Damascus",
        "interests": "sports",
    }


def test_profile_get_returns_404_when_profile_is_missing(
    client, authenticate, make_user
):
    user = make_user("noprofile@example.com", UserType.RESPONDENT)
    authenticate(user)

    response = client.get(PROFILE_URL)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_profile_put_updates_and_persists(client, authenticate, respondent):
    authenticate(respondent)
    payload = {
        "age": 41,
        "gender": "FEMALE",
        "region": "Homs",
        "interests": "music",
    }

    response = client.put(PROFILE_URL, payload, format="json")

    assert response.status_code == 200
    assert response.json() == payload
    profile = RespondentProfile.objects.get(user=respondent)
    assert (profile.age, profile.gender, profile.region, profile.interests) == (
        41,
        "FEMALE",
        "Homs",
        "music",
    )


def test_profile_put_creates_missing_profile(client, authenticate, make_user):
    user = make_user("noprofile@example.com", UserType.RESPONDENT)
    authenticate(user)
    payload = {"age": 25, "gender": "MALE", "region": "Latakia", "interests": "chess"}

    response = client.put(PROFILE_URL, payload, format="json")

    assert response.status_code == 200
    assert RespondentProfile.objects.filter(user=user).exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("age", 0),
        ("age", 121),
        ("age", "abc"),
        ("age", True),
        ("gender", "ANY"),
        ("gender", "OTHER"),
        ("region", ""),
    ],
)
def test_profile_put_rejects_invalid_field(
    client, authenticate, respondent, field, value
):
    authenticate(respondent)
    payload = {"age": 41, "gender": "FEMALE", "region": "Homs", "interests": "music"}
    payload[field] = value

    response = client.put(PROFILE_URL, payload, format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert RespondentProfile.objects.get(user=respondent).age == 30


def test_profile_put_requires_all_fields(client, authenticate, respondent):
    authenticate(respondent)

    response = client.put(PROFILE_URL, {}, format="json")

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {
        "age",
        "gender",
        "region",
        "interests",
    }


def test_profile_patch_is_not_allowed(client, authenticate, respondent):
    authenticate(respondent)

    response = client.patch(PROFILE_URL, {"age": 40}, format="json")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
