"""FR-15 Part A: POST /surveys/{id}/responses/ is throttled per respondent (scope survey_submit)."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from tests.api.conftest import PASSWORD

TOKEN_URL = "/api/v1/auth/token/"
LIMIT = 10

pytestmark = pytest.mark.django_db


def submit_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/responses/"


def valid_answers(survey):
    choice, rating, _text = survey.questions.order_by("order_index")
    option = choice.options.order_by("order_index").first()
    return [
        {"question_id": choice.question_id, "selected_option_id": option.option_id},
        {"question_id": rating.question_id, "rating_value": 4},
    ]


def submit_times(client, survey, times):
    payload = {"answers": valid_answers(survey)}
    return [client.post(submit_url(survey), payload, format="json") for _ in range(times)]


def test_submits_up_to_the_limit_get_their_normal_answer(authenticate, respondent, survey):
    responses = submit_times(authenticate(respondent), survey, LIMIT)

    assert [r.status_code for r in responses] == [201] + [409] * (LIMIT - 1)
    assert {r.json()["error"]["code"] for r in responses[1:]} == {"duplicate_response"}


def test_submit_after_the_limit_is_throttled(authenticate, respondent, survey):
    client = authenticate(respondent)
    submit_times(client, survey, LIMIT)

    response = submit_times(client, survey, 1)[0]

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"
    assert int(response["Retry-After"]) > 0


def test_another_respondent_is_not_throttled_by_the_first(
    authenticate, respondent, make_respondent, survey
):
    first = authenticate(respondent)
    submit_times(first, survey, LIMIT + 1)

    other = make_respondent(email="other@example.com")
    other_client = APIClient()
    other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(other)}")
    response = submit_times(other_client, survey, 1)[0]

    assert response.status_code == 201


def test_using_up_submit_does_not_throttle_login(authenticate, respondent, survey):
    throttled = submit_times(authenticate(respondent), survey, LIMIT + 1)[-1]

    login = APIClient().post(
        TOKEN_URL, {"email": respondent.email, "password": PASSWORD}, format="json"
    )

    assert throttled.status_code == 429
    assert login.status_code == 200
