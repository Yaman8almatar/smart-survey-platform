import pytest

from apps.core.models import Response
from core.enums import Gender, SurveyStatus

ELIGIBLE_URL = "/api/v1/surveys/eligible/"

pytestmark = pytest.mark.django_db


def detail_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/"


def test_eligible_lists_matching_survey_with_question_count(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    response = client.get(ELIGIBLE_URL)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": survey.survey_id,
            "title": "Campus survey",
            "description": "About campus life",
            "question_count": 3,
        }
    ]


def test_eligible_is_empty_when_nothing_matches(client, authenticate, respondent):
    authenticate(respondent)

    response = client.get(ELIGIBLE_URL)

    assert response.status_code == 200
    assert response.json() == []


def test_eligible_excludes_surveys_that_do_not_match_the_profile(
    client, authenticate, respondent, make_survey
):
    make_survey(title="Wrong region", region="Aleppo")
    make_survey(title="Wrong gender", gender=Gender.FEMALE)
    make_survey(title="Too old", age_max=20)
    authenticate(respondent)

    response = client.get(ELIGIBLE_URL)

    assert response.json() == []


@pytest.mark.parametrize("status", [SurveyStatus.DRAFT, SurveyStatus.CLOSED])
def test_eligible_excludes_unpublished_surveys(
    client, authenticate, respondent, make_survey, status
):
    make_survey(status=status)
    authenticate(respondent)

    response = client.get(ELIGIBLE_URL)

    assert response.json() == []


def test_eligible_excludes_already_answered_surveys(
    client, authenticate, respondent, survey
):
    Response.objects.create(survey=survey, respondent=respondent)
    authenticate(respondent)

    response = client.get(ELIGIBLE_URL)

    assert response.json() == []


def test_detail_returns_survey_with_ordered_questions_and_options(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    response = client.get(detail_url(survey))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == survey.survey_id
    assert body["title"] == "Campus survey"
    assert body["description"] == "About campus life"
    questions = body["questions"]
    assert [q["text"] for q in questions] == ["Pick one", "Rate us", "Comments"]
    assert [q["type"] for q in questions] == [
        "MULTIPLE_CHOICE",
        "RATING_SCALE",
        "OPEN_TEXT",
    ]
    assert [q["is_required"] for q in questions] == [True, True, False]
    assert [o["text"] for o in questions[0]["options"]] == ["A", "B"]
    assert set(questions[0]["options"][0]) == {"id", "text"}
    assert questions[1]["rating_values"] == [1, 2, 3, 4, 5]
    assert questions[0]["rating_values"] == []
    assert set(questions[0]) == {
        "id",
        "text",
        "type",
        "is_required",
        "order_index",
        "options",
        "rating_values",
    }


def test_detail_returns_403_when_not_eligible(
    client, authenticate, respondent, make_survey
):
    other = make_survey(gender=Gender.FEMALE)
    authenticate(respondent)

    response = client.get(detail_url(other))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unauthorized_action"


def test_detail_returns_404_when_missing(client, authenticate, respondent):
    authenticate(respondent)

    response = client.get("/api/v1/surveys/999999/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "survey_not_found"


@pytest.mark.parametrize("status", [SurveyStatus.DRAFT, SurveyStatus.CLOSED])
def test_detail_returns_409_when_survey_is_not_published(
    client, authenticate, respondent, make_survey, status
):
    unpublished = make_survey(status=status)
    authenticate(respondent)

    response = client.get(detail_url(unpublished))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_editable"
