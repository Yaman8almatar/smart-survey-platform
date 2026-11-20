"""FR-16: the order settings of a survey and the respondent's own order (TASK-52)."""

import pytest

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import NotEditable, ValidationError
from services.question_service import QuestionService
from services.survey_service import SurveyService

pytestmark = pytest.mark.django_db

CHOICE_TEXTS = ["Red", "Green", "Blue", "Yellow", "Black"]


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_respondent(index):
    user = create_user(f"respondent-shuffle-{index}@example.com", UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=user, age=30, gender=Gender.MALE, region="DAMASCUS", interests=["SPORTS"]
    )
    return user


@pytest.fixture
def provider():
    return create_user("provider-shuffle@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def respondents():
    return [create_respondent(index) for index in range(10)]


def make_survey(provider, shuffle_questions=False, shuffle_options=False):
    """Published survey: a choice with five options, a rating, then four open-text questions.

    Stored order_index values are 10, 20, ... so a renumbering is visible.
    """
    survey = Survey.objects.create(
        provider=provider,
        title="Shuffle survey",
        description="D",
        status=SurveyStatus.PUBLISHED,
        shuffle_questions=shuffle_questions,
        shuffle_options=shuffle_options,
    )
    TargetingCriteria.objects.create(survey=survey)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick a colour",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=10,
    )
    for index, text in enumerate(CHOICE_TEXTS):
        QuestionOption.objects.create(question=choice, option_text=text, order_index=index)
    Question.objects.create(
        survey=survey,
        question_text="Rate us",
        question_type=QuestionType.RATING_SCALE,
        is_required=True,
        order_index=20,
    )
    for number in range(4):
        Question.objects.create(
            survey=survey,
            question_text=f"Comment {number}",
            question_type=QuestionType.OPEN_TEXT,
            is_required=False,
            order_index=30 + number * 10,
        )
    return survey


def form_of(respondent, survey):
    return QuestionService().get_response_form(respondent, survey.survey_id)["questions"]


def stored_questions(survey):
    return list(survey.questions.order_by("order_index", "question_id"))


def question_ids(rows):
    return [row["question_id"] for row in rows]


def choice_row(rows):
    return next(row for row in rows if row["is_multiple_choice"])


def rating_row(rows):
    return next(row for row in rows if row["is_rating_scale"])


# Settings


def test_create_stores_both_settings(provider):
    survey = SurveyService().create_survey(
        provider, "T", "D", shuffle_questions=True, shuffle_options=False
    )
    survey.refresh_from_db()

    assert (survey.shuffle_questions, survey.shuffle_options) == (True, False)


def test_create_without_settings_keeps_both_off(provider):
    survey = SurveyService().create_survey(provider, "T", "D")
    survey.refresh_from_db()

    assert (survey.shuffle_questions, survey.shuffle_options) == (False, False)


def test_update_stores_both_settings(provider):
    service = SurveyService()
    survey = service.create_survey(provider, "T", "D")

    service.update_survey(
        provider, survey.survey_id, "T", "D", shuffle_questions=False, shuffle_options=True
    )
    survey.refresh_from_db()

    assert (survey.shuffle_questions, survey.shuffle_options) == (False, True)


@pytest.mark.parametrize(
    "order_settings",
    [
        {"shuffle_questions": "yes"},
        {"shuffle_options": 1},
        {"shuffle_questions": None},
    ],
)
def test_a_setting_that_is_not_a_bool_is_refused(provider, order_settings):
    service = SurveyService()
    with pytest.raises(ValidationError, match="Shuffle settings must be true or false."):
        service.create_survey(provider, "T", "D", **order_settings)

    survey = service.create_survey(provider, "T", "D")
    with pytest.raises(ValidationError, match="Shuffle settings must be true or false."):
        service.update_survey(provider, survey.survey_id, "T", "D", **order_settings)


def test_update_of_a_published_survey_stays_refused(provider):
    survey = make_survey(provider)

    with pytest.raises(NotEditable):
        SurveyService().update_survey(
            provider, survey.survey_id, "T", "D", shuffle_questions=True, shuffle_options=True
        )
    survey.refresh_from_db()

    assert (survey.shuffle_questions, survey.shuffle_options) == (False, False)


# The respondent's form


def test_with_both_off_the_form_keeps_the_provider_order_and_fields(provider, respondents):
    survey = make_survey(provider)

    rows = form_of(respondents[0], survey)

    stored = stored_questions(survey)
    assert question_ids(rows) == [question.question_id for question in stored]
    assert [row["order_index"] for row in rows] == [10, 20, 30, 40, 50, 60]
    choice = choice_row(rows)
    assert [option["text"] for option in choice["options"]] == CHOICE_TEXTS
    assert [option["order_index"] for option in choice["options"]] == [0, 1, 2, 3, 4]
    assert set(choice) == {
        "question_id",
        "question_text",
        "question_type",
        "is_required",
        "order_index",
        "options",
        "id",
        "text",
        "type_label",
        "required_label",
        "is_open_text",
        "is_rating_scale",
        "is_multiple_choice",
        "answer_name",
        "rating_name",
        "option_name",
        "rating_values",
    }


def test_with_questions_on_order_index_runs_from_zero_in_the_shuffled_order(
    provider, respondents
):
    survey = make_survey(provider, shuffle_questions=True)

    rows = form_of(respondents[0], survey)

    assert [row["order_index"] for row in rows] == list(range(6))
    assert sorted(question_ids(rows)) == sorted(q.question_id for q in stored_questions(survey))


def test_with_questions_on_two_calls_give_the_same_order(provider, respondents):
    survey = make_survey(provider, shuffle_questions=True)

    assert question_ids(form_of(respondents[0], survey)) == question_ids(
        form_of(respondents[0], survey)
    )


def test_with_questions_on_respondents_get_different_orders(provider, respondents):
    survey = make_survey(provider, shuffle_questions=True)

    orders = {tuple(question_ids(form_of(respondent, survey))) for respondent in respondents}

    assert len(orders) >= 2


def test_with_options_on_choices_are_a_permutation_and_ratings_unchanged(
    provider, respondents
):
    survey = make_survey(provider, shuffle_options=True)

    orders = set()
    for respondent in respondents:
        rows = form_of(respondent, survey)
        options = choice_row(rows)["options"]
        assert sorted(option["text"] for option in options) == sorted(CHOICE_TEXTS)
        orders.add(tuple(option["text"] for option in options))
        rating = rating_row(rows)
        assert rating["options"] == []
        assert rating["rating_values"] == [1, 2, 3, 4, 5]
        assert rating["order_index"] == 20
    assert len(orders) >= 2


def test_options_on_with_questions_off_keeps_the_question_order(provider, respondents):
    survey = make_survey(provider, shuffle_options=True)

    rows = form_of(respondents[0], survey)

    assert question_ids(rows) == [q.question_id for q in stored_questions(survey)]
    assert [row["order_index"] for row in rows] == [10, 20, 30, 40, 50, 60]


def test_the_provider_page_keeps_the_provider_order_when_both_are_on(provider):
    survey = make_survey(provider, shuffle_questions=True, shuffle_options=True)

    rows = QuestionService().get_survey_question_rows(provider, survey.survey_id)

    assert [row["question_id"] for row in rows] == [
        q.question_id for q in stored_questions(survey)
    ]
    assert [option["option_text"] for option in rows[0]["options"]] == CHOICE_TEXTS
