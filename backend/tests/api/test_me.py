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
        "region": "DAMASCUS",
        "interests": ["SPORTS"],
        "education": "",
        "occupation": "",
        "marital_status": "",
        "completion_percent": 57,
    }


def test_profile_get_returns_optional_fields_and_completion(
    client, authenticate, respondent
):
    RespondentProfile.objects.filter(user=respondent).update(
        education="PREFER_NOT_TO_SAY", occupation="STUDENT"
    )
    authenticate(respondent)

    body = client.get(PROFILE_URL).json()

    assert (body["education"], body["occupation"], body["marital_status"]) == (
        "PREFER_NOT_TO_SAY",
        "STUDENT",
        "",
    )
    assert body["completion_percent"] == 86


def test_profile_get_returns_404_when_profile_is_missing(
    client, authenticate, make_user
):
    user = make_user("noprofile@example.com", UserType.RESPONDENT)
    authenticate(user)

    response = client.get(PROFILE_URL)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


FULL_PAYLOAD = {
    "age": 41,
    "gender": "FEMALE",
    "region": "HOMS",
    "interests": ["ENTERTAINMENT", "FOOD"],
    "education": "MASTER",
    "occupation": "PUBLIC_SECTOR",
    "marital_status": "MARRIED",
}


def test_profile_put_updates_and_persists(client, authenticate, respondent):
    authenticate(respondent)

    response = client.put(PROFILE_URL, FULL_PAYLOAD, format="json")

    assert response.status_code == 200
    assert response.json() == {**FULL_PAYLOAD, "completion_percent": 100}
    profile = RespondentProfile.objects.get(user=respondent)
    assert (
        profile.age,
        profile.gender,
        profile.region,
        profile.interests,
        profile.education,
        profile.occupation,
        profile.marital_status,
    ) == (41, "FEMALE", "HOMS", ["ENTERTAINMENT", "FOOD"], "MASTER", "PUBLIC_SECTOR", "MARRIED")


def test_profile_put_omitting_optional_fields_stores_empty(
    client, authenticate, respondent
):
    authenticate(respondent)
    client.put(PROFILE_URL, FULL_PAYLOAD, format="json")
    payload = {key: FULL_PAYLOAD[key] for key in ("age", "gender", "region", "interests")}

    response = client.put(PROFILE_URL, payload, format="json")

    assert response.status_code == 200
    assert response.json()["completion_percent"] == 57
    profile = RespondentProfile.objects.get(user=respondent)
    assert (profile.education, profile.occupation, profile.marital_status) == ("", "", "")


def test_profile_put_creates_missing_profile(client, authenticate, make_user):
    user = make_user("noprofile@example.com", UserType.RESPONDENT)
    authenticate(user)
    payload = {"age": 25, "gender": "MALE", "region": "LATAKIA", "interests": ["ARTS"]}

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
        ("region", "Homs"),
        ("region", "HOMS "),
        ("interests", []),
        ("interests", "FOOD"),
        ("interests", ["MUSIC"]),
        ("interests", ["FOOD", "FOOD"]),
        ("education", "PHD"),
        ("occupation", "ENGINEER"),
        ("marital_status", "ENGAGED"),
    ],
)
def test_profile_put_rejects_invalid_field(
    client, authenticate, respondent, field, value
):
    authenticate(respondent)
    payload = {**FULL_PAYLOAD, field: value}

    response = client.put(PROFILE_URL, payload, format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert RespondentProfile.objects.get(user=respondent).age == 30


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("region", "Homs", "Choose a governorate from the list."),
        ("interests", [], "Choose at least one interest."),
    ],
)
def test_profile_put_field_errors_name_the_field(
    client, authenticate, respondent, field, value, message
):
    authenticate(respondent)

    response = client.put(PROFILE_URL, {**FULL_PAYLOAD, field: value}, format="json")

    assert response.json()["error"]["fields"][field] == [message]


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
