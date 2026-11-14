"""Draft endpoints (FR-06): save, load and delete a respondent's unsent answers."""

import pytest
from django.db import IntegrityError, transaction

from apps.core.models import ResponseDraft

pytestmark = pytest.mark.django_db


def draft_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/draft/"


def questions(survey):
    return list(survey.questions.order_by("order_index"))


def choice_draft(survey):
    choice = questions(survey)[0]
    option = choice.options.order_by("order_index").first()
    return [{"question_id": choice.question_id, "selected_option_id": option.option_id}]


def save(client, survey, answers):
    return client.put(draft_url(survey), {"answers": answers}, format="json")


def test_get_without_draft_returns_404(client, authenticate, respondent, survey):
    authenticate(respondent)

    response = client.get(draft_url(survey))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "draft_not_found"


def test_put_returns_the_stored_shape(client, authenticate, respondent, survey):
    authenticate(respondent)
    answers = choice_draft(survey)

    response = save(client, survey, answers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"survey_id", "answers", "started_at", "updated_at"}
    assert body["survey_id"] == survey.survey_id
    assert body["answers"] == answers


def test_get_returns_the_saved_draft(client, authenticate, respondent, survey):
    authenticate(respondent)
    answers = choice_draft(survey)
    saved = save(client, survey, answers).json()

    response = client.get(draft_url(survey))

    assert response.status_code == 200
    assert response.json() == saved


def test_put_replaces_answers_and_keeps_started_at(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    first = save(client, survey, choice_draft(survey)).json()
    text = questions(survey)[2]
    answers = [{"question_id": text.question_id, "answer_value": "Still thinking"}]

    second = save(client, survey, answers).json()

    assert second["answers"] == answers
    assert second["started_at"] == first["started_at"]


def test_delete_returns_204_then_get_returns_404(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    save(client, survey, choice_draft(survey))

    deleted = client.delete(draft_url(survey))
    after = client.get(draft_url(survey))

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert after.status_code == 404
    assert after.json()["error"]["code"] == "draft_not_found"


def test_put_rejects_answer_value_over_2000_characters(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    text = questions(survey)[2]

    response = save(
        client, survey, [{"question_id": text.question_id, "answer_value": "x" * 2001}]
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert not ResponseDraft.objects.filter(survey=survey).exists()


def test_put_with_a_question_of_another_survey_returns_404(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    response = save(
        client, survey, [{"question_id": 999999, "answer_value": "Elsewhere"}]
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "question_not_found"


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_unauthenticated_returns_401(client, survey, method):
    response = getattr(client, method)(draft_url(survey), {}, format="json")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_submit_deletes_the_draft_and_get_returns_409(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    answers = choice_draft(survey)
    save(client, survey, answers)
    rating = questions(survey)[1]
    answers.append({"question_id": rating.question_id, "rating_value": 4})

    submitted = client.post(
        f"/api/v1/surveys/{survey.survey_id}/responses/",
        {"answers": answers},
        format="json",
    )
    after = client.get(draft_url(survey))

    assert submitted.status_code == 201
    assert after.status_code == 409
    assert after.json()["error"]["code"] == "duplicate_response"
    assert not ResponseDraft.objects.filter(survey=survey).exists()


def test_unique_constraint_rejects_a_second_row(respondent, survey):
    ResponseDraft.objects.create(survey=survey, respondent=respondent)

    with pytest.raises(IntegrityError), transaction.atomic():
        ResponseDraft.objects.create(survey=survey, respondent=respondent)
