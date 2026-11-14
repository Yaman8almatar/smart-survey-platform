import pytest

from core.enums import Education, Governorate, Interest, MaritalStatus, Occupation

OPTIONS_URL = "/api/v1/profile/options/"

pytestmark = pytest.mark.django_db


def codes(items):
    return [item["code"] for item in items]


def test_options_are_public(client):
    response = client.get(OPTIONS_URL)

    assert response.status_code == 200


def test_options_are_public_even_with_a_bad_token(client):
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

    response = client.get(OPTIONS_URL)

    assert response.status_code == 200


def test_options_return_the_five_lists_in_order(client):
    body = client.get(OPTIONS_URL).json()

    assert list(body) == [
        "governorates",
        "education",
        "occupation",
        "marital_status",
        "interests",
    ]
    assert codes(body["governorates"]) == Governorate.values
    assert codes(body["education"]) == Education.values
    assert codes(body["occupation"]) == Occupation.values
    assert codes(body["marital_status"]) == MaritalStatus.values
    assert codes(body["interests"]) == Interest.values
    assert body["governorates"][0] == {"code": "ALEPPO", "label": "Aleppo"}


def test_governorates_end_with_outside_syria(client):
    body = client.get(OPTIONS_URL).json()

    assert body["governorates"][-1] == {"code": "OUTSIDE_SYRIA", "label": "Outside Syria"}


@pytest.mark.parametrize("key", ["education", "occupation", "marital_status"])
def test_optional_lists_end_with_prefer_not_to_say(client, key):
    body = client.get(OPTIONS_URL).json()

    assert body[key][-1] == {"code": "PREFER_NOT_TO_SAY", "label": "Prefer not to say"}
