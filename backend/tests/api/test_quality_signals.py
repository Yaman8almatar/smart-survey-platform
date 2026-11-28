"""FR-04 Part 1 (TASK-41): optional timings and device_id on draft save and submit."""

import pytest

from apps.core.models import Question, Response, ResponseQuality

pytestmark = pytest.mark.django_db

DEVICE = "3f9c2a7e-51b4-4d0e-9a3c-7b1d2e8f6a40"
QUESTION_KEYS = {"id", "text", "type", "is_required", "order_index", "options", "rating_values"}


def submit_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/responses/"


def draft_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/draft/"


def valid_answers(survey):
    choice, rating, _ = survey.questions.order_by("order_index")
    option = choice.options.order_by("order_index").first()
    return [
        {"question_id": choice.question_id, "selected_option_id": option.option_id},
        {"question_id": rating.question_id, "rating_value": 4},
    ]


def timings(survey, active_ms=1000):
    return [
        {"question_id": q.question_id, "active_ms": active_ms}
        for q in survey.questions.order_by("order_index")
    ]


def first_question_id(survey):
    return survey.questions.order_by("order_index").first().question_id


def test_submit_without_evidence_returns_201_and_stores_signals_ok_false(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    response = client.post(submit_url(survey), {"answers": valid_answers(survey)}, format="json")

    assert response.status_code == 201
    assert set(response.json()) == {"id", "survey_id", "submitted_at"}
    quality = ResponseQuality.objects.get(response_id=response.json()["id"])
    assert quality.signals_ok is False
    assert quality.timings == []
    assert quality.device_hash == ""


def test_submit_with_evidence_after_a_draft_stores_signals_ok_true(
    client, authenticate, respondent, survey
):
    authenticate(respondent)
    client.put(draft_url(survey), {"answers": [], "timings": timings(survey, 500)}, format="json")

    response = client.post(
        submit_url(survey),
        {"answers": valid_answers(survey), "timings": timings(survey), "device_id": DEVICE},
        format="json",
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id", "survey_id", "submitted_at"}
    quality = ResponseQuality.objects.get(response_id=response.json()["id"])
    assert quality.timings == timings(survey)
    assert quality.active_ms == 3000
    assert quality.signals_ok is True


def test_draft_put_returns_timings_and_keeps_them_without_the_key(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    first = client.put(draft_url(survey), {"answers": []}, format="json").json()
    second = client.put(
        draft_url(survey), {"answers": [], "timings": timings(survey, 700)}, format="json"
    ).json()
    third = client.put(draft_url(survey), {"answers": []}, format="json").json()

    assert first["timings"] == []
    assert second["timings"] == timings(survey, 700)
    assert third["timings"] == timings(survey, 700)
    assert client.get(draft_url(survey)).json()["timings"] == timings(survey, 700)


def bad_timings(survey):
    question_id = first_question_id(survey)
    return [
        "not a list",
        ["not a dict"],
        [{"question_id": question_id}],
        [{"question_id": question_id, "active_ms": -1}],
        [{"question_id": question_id, "active_ms": 3_600_001}],
        [
            {"question_id": question_id, "active_ms": 10},
            {"question_id": question_id, "active_ms": 20},
        ],
    ]


@pytest.mark.parametrize("case", range(6))
def test_submit_rejects_bad_timings_with_400(client, authenticate, respondent, survey, case):
    authenticate(respondent)
    body = {"answers": valid_answers(survey), "timings": bad_timings(survey)[case]}

    response = client.post(submit_url(survey), body, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert not Response.objects.filter(survey=survey).exists()


@pytest.mark.parametrize("case", range(6))
def test_draft_put_rejects_bad_timings_with_400(client, authenticate, respondent, survey, case):
    authenticate(respondent)

    response = client.put(
        draft_url(survey), {"answers": [], "timings": bad_timings(survey)[case]}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_timing_for_a_question_outside_the_survey_gives_404(
    client, authenticate, respondent, survey, make_survey
):
    other = make_survey(title="Other")
    foreign = Question.objects.create(
        survey=other, question_text="Elsewhere", question_type="OPEN_TEXT", order_index=0
    )
    foreign_timings = [{"question_id": foreign.question_id, "active_ms": 10}]
    authenticate(respondent)

    submitted = client.post(
        submit_url(survey),
        {"answers": valid_answers(survey), "timings": foreign_timings},
        format="json",
    )
    drafted = client.put(
        draft_url(survey), {"answers": [], "timings": foreign_timings}, format="json"
    )

    assert submitted.status_code == 404
    assert submitted.json()["error"]["code"] == "question_not_found"
    assert drafted.status_code == 404
    assert drafted.json()["error"]["code"] == "question_not_found"
    assert not Response.objects.filter(survey=survey).exists()


@pytest.mark.parametrize(
    "device_id", ["short-id", "x" * 65, "has space in it 1234", "bad*chars*0123456789", 12345]
)
def test_submit_rejects_a_bad_device_id_with_400_without_echoing_it(
    client, authenticate, respondent, survey, device_id
):
    authenticate(respondent)

    response = client.post(
        submit_url(survey),
        {"answers": valid_answers(survey), "device_id": device_id},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert str(device_id) not in response.content.decode()
    assert not Response.objects.filter(survey=survey).exists()


def test_attention_fields_never_leave_the_server(client, authenticate, respondent, survey):
    choice, rating, _ = survey.questions.order_by("order_index")
    Question.objects.filter(pk=choice.pk).update(
        is_attention_check=True, expected_option=choice.options.order_by("order_index").last()
    )
    Question.objects.filter(pk=rating.pk).update(is_attention_check=True, expected_rating=2)
    authenticate(respondent)

    response = client.get(f"/api/v1/surveys/{survey.survey_id}/")

    assert response.status_code == 200
    for question in response.json()["questions"]:
        assert set(question) == QUESTION_KEYS
    content = response.content.decode()
    assert "attention" not in content
    assert "expected" not in content
