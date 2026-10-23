import pytest

from apps.core.models import Answer, Question, QuestionOption, Response
from core.enums import Gender, QuestionType, SurveyStatus

HISTORY_URL = "/api/v1/me/responses/"

pytestmark = pytest.mark.django_db


def submit_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/responses/"


def valid_answers(survey):
    choice, rating, text = survey.questions.order_by("order_index")
    option = choice.options.order_by("order_index").first()
    return [
        {"question_id": choice.question_id, "selected_option_id": option.option_id},
        {"question_id": rating.question_id, "rating_value": 4},
        {"question_id": text.question_id, "answer_value": "Great place"},
    ]


def submit(client, survey, answers):
    return client.post(submit_url(survey), {"answers": answers}, format="json")


def test_submit_stores_response_and_answers(client, authenticate, respondent, survey):
    authenticate(respondent)

    response = submit(client, survey, valid_answers(survey))

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "survey_id", "submitted_at"}
    assert body["survey_id"] == survey.survey_id
    stored = Response.objects.get(response_id=body["id"])
    assert stored.respondent_id == respondent.user_id
    assert Answer.objects.filter(response=stored).count() == 3


def test_submit_accepts_missing_optional_answer(client, authenticate, respondent, survey):
    authenticate(respondent)

    response = submit(client, survey, valid_answers(survey)[:2])

    assert response.status_code == 201
    assert Answer.objects.filter(response_id=response.json()["id"]).count() == 2


def test_submitted_survey_moves_from_eligible_to_history(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    submit(client, survey, valid_answers(survey))

    eligible = client.get("/api/v1/surveys/eligible/").json()
    history = client.get(HISTORY_URL)

    assert eligible == []
    assert history.status_code == 200
    assert [row["survey_id"] for row in history.json()] == [survey.survey_id]


def test_submit_twice_returns_409_duplicate(client, authenticate, respondent, survey):
    authenticate(respondent)
    submit(client, survey, valid_answers(survey))

    response = submit(client, survey, valid_answers(survey))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_response"
    assert Response.objects.filter(survey=survey, respondent=respondent).count() == 1


def test_submit_returns_403_when_not_eligible(
    client, authenticate, respondent, make_survey
):
    other = make_survey(gender=Gender.FEMALE)
    authenticate(respondent)

    response = submit(client, other, [])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "unauthorized_action"


def test_submit_returns_404_when_survey_is_missing(client, authenticate, respondent):
    authenticate(respondent)

    response = client.post(
        "/api/v1/surveys/999999/responses/", {"answers": []}, format="json"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "survey_not_found"


@pytest.mark.parametrize("status", [SurveyStatus.DRAFT, SurveyStatus.CLOSED])
def test_submit_returns_409_when_survey_is_not_published(
    client, authenticate, respondent, make_survey, status
):
    unpublished = make_survey(status=status)
    authenticate(respondent)

    response = submit(client, unpublished, [])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_editable"


def test_submit_without_required_answer_returns_400(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    response = submit(client, survey, valid_answers(survey)[:1])

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert not Response.objects.filter(respondent=respondent).exists()


def test_submit_with_rating_out_of_range_returns_400(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    answers = valid_answers(survey)
    answers[1]["rating_value"] = 6

    response = submit(client, survey, answers)

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Rating value must be an integer from 1 to 5."


def test_submit_with_option_of_another_question_returns_400(
    client, authenticate, respondent, survey, make_survey
):
    foreign = Question.objects.create(
        survey=make_survey(title="Other"),
        question_text="Other choice",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=0,
    )
    foreign_option = QuestionOption.objects.create(
        question=foreign, option_text="X", order_index=0
    )
    authenticate(respondent)
    answers = valid_answers(survey)
    answers[0]["selected_option_id"] = foreign_option.option_id

    response = submit(client, survey, answers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_submit_with_duplicate_question_answers_returns_400(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    answers = valid_answers(survey)
    answers.append(dict(answers[1]))

    response = submit(client, survey, answers)

    assert response.status_code == 400


def test_submit_with_unknown_question_returns_404(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    answers = valid_answers(survey) + [{"question_id": 999999, "answer_value": "?"}]

    response = submit(client, survey, answers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "question_not_found"
    assert not Response.objects.filter(respondent=respondent).exists()


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"answers": "nope"},
        {"answers": ["nope"]},
        {"answers": [{"answer_value": "no question id"}]},
        {"answers": [{"question_id": 1, "rating_value": True}]},
    ],
)
def test_submit_with_malformed_body_returns_400_with_fields(
    client, authenticate, respondent, survey, body
):
    authenticate(respondent)

    response = client.post(submit_url(survey), body, format="json")

    assert response.status_code == 400
    assert "answers" in response.json()["error"]["fields"]


def test_history_lists_only_own_responses(
    client, authenticate, respondent, make_respondent, survey
):
    other = make_respondent(email="other@example.com")
    Response.objects.create(survey=survey, respondent=other)
    authenticate(respondent)

    assert client.get(HISTORY_URL).json() == []

    submit(client, survey, valid_answers(survey))
    rows = client.get(HISTORY_URL).json()

    assert len(rows) == 1
    assert set(rows[0]) == {"survey_id", "title", "description", "submitted_at"}
    assert rows[0]["title"] == "Campus survey"
