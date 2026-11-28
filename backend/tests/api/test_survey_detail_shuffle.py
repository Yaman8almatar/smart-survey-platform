"""FR-16: the survey detail carries the respondent's own order (TASK-52)."""

import pytest

from apps.core.models import Question, QuestionOption
from core.enums import QuestionType
from services.presentation_order import respondent_order

pytestmark = pytest.mark.django_db


def detail_url(survey):
    return f"/api/v1/surveys/{survey.survey_id}/"


@pytest.fixture
def wide_survey(make_survey):
    """Published survey: a choice with five options, a rating and four open-text questions."""
    survey = make_survey()
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick a colour",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=0,
    )
    for index, text in enumerate(["Red", "Green", "Blue", "Yellow", "Black"]):
        QuestionOption.objects.create(question=choice, option_text=text, order_index=index)
    Question.objects.create(
        survey=survey,
        question_text="Rate us",
        question_type=QuestionType.RATING_SCALE,
        is_required=True,
        order_index=1,
    )
    for number in range(4):
        Question.objects.create(
            survey=survey,
            question_text=f"Comment {number}",
            question_type=QuestionType.OPEN_TEXT,
            is_required=False,
            order_index=2 + number,
        )
    return survey


def turn_on(survey, questions=True, options=True):
    survey.shuffle_questions = questions
    survey.shuffle_options = options
    survey.save()


def test_detail_with_both_on_carries_the_shuffled_order(
    client, authenticate, respondent, wide_survey
):
    turn_on(wide_survey)
    authenticate(respondent)

    body = client.get(detail_url(wide_survey)).json()

    stored = list(wide_survey.questions.order_by("order_index"))
    expected = respondent_order(
        stored, lambda q: q.question_id, wide_survey.survey_id, respondent.user_id, "questions"
    )
    questions = body["questions"]
    assert [q["id"] for q in questions] == [q.question_id for q in expected]
    assert [q["order_index"] for q in questions] == list(range(len(stored)))

    choice = next(q for q in questions if q["type"] == "MULTIPLE_CHOICE")
    options = list(QuestionOption.objects.filter(question_id=choice["id"]))
    expected_options = respondent_order(
        options,
        lambda o: o.option_id,
        wide_survey.survey_id,
        respondent.user_id,
        f"options:{choice['id']}",
    )
    assert [o["id"] for o in choice["options"]] == [o.option_id for o in expected_options]


def test_detail_with_both_off_is_todays_payload(client, authenticate, respondent, survey):
    authenticate(respondent)

    questions = client.get(detail_url(survey)).json()["questions"]

    assert [q["text"] for q in questions] == ["Pick one", "Rate us", "Comments"]
    assert [q["order_index"] for q in questions] == [0, 1, 2]
    assert [o["text"] for o in questions[0]["options"]] == ["A", "B"]
    assert set(questions[0]) == {
        "id",
        "text",
        "type",
        "is_required",
        "order_index",
        "options",
        "rating_values",
    }
    assert set(questions[0]["options"][0]) == {"id", "text"}


def test_a_saved_draft_fetched_again_keeps_the_same_order(
    client, authenticate, respondent, wide_survey
):
    turn_on(wide_survey)
    authenticate(respondent)
    first = client.get(detail_url(wide_survey)).json()
    choice = next(q for q in first["questions"] if q["type"] == "MULTIPLE_CHOICE")
    answers = [{"question_id": choice["id"], "selected_option_id": choice["options"][0]["id"]}]

    saved = client.put(
        f"/api/v1/surveys/{wide_survey.survey_id}/draft/", {"answers": answers}, format="json"
    )
    again = client.get(detail_url(wide_survey)).json()

    assert saved.status_code == 200
    assert again == first
