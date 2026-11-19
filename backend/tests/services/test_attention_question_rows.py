"""TASK-43: the two-option rule of a choice attention check and the provider's question rows."""

import pytest

from apps.core.models import Question, Survey, TargetingCriteria, User
from core.enums import AccountStatus, QuestionType, UserType
from core.exceptions import ValidationError
from services.question_service import QuestionService

pytestmark = pytest.mark.django_db

OPTION_KEYS = {"option_id", "option_text", "order_index"}


@pytest.fixture
def provider():
    return User.objects.create_user(
        email="provider-rows@example.com",
        password="strong-password",
        name="Test User",
        user_type=UserType.SERVICE_PROVIDER,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def survey(provider):
    survey = Survey.objects.create(provider=provider, title="Rows")
    TargetingCriteria.objects.create(survey=survey, regions=[], gender=None)
    return survey


def add(provider, survey, question_type, order_index=0, options=None, **kwargs):
    return QuestionService().add_question_with_options(
        provider,
        survey.survey_id,
        f"Question {order_index}",
        question_type,
        False,
        order_index,
        options=options,
        **kwargs,
    )


@pytest.mark.parametrize("options", [["Only"], ["Only", "  "]])
def test_a_choice_attention_check_needs_two_options(provider, survey, options):
    with pytest.raises(
        ValidationError, match="^Add at least two options, then choose the expected one.$"
    ):
        add(
            provider,
            survey,
            QuestionType.MULTIPLE_CHOICE,
            options=options,
            is_attention_check=True,
            expected_option_index=0,
        )

    assert not Question.objects.filter(survey=survey).exists()


def test_the_two_option_rule_comes_before_the_expected_answer(provider, survey):
    with pytest.raises(
        ValidationError, match="^Add at least two options, then choose the expected one.$"
    ):
        add(
            provider,
            survey,
            QuestionType.MULTIPLE_CHOICE,
            options=["Only"],
            is_attention_check=True,
        )


def rows_by_order(provider, survey):
    rows = QuestionService().get_survey_question_rows(provider, survey.survey_id)
    return {row["order_index"]: row for row in rows}


def test_rows_carry_the_attention_fields(provider, survey):
    choice = add(
        provider,
        survey,
        QuestionType.MULTIPLE_CHOICE,
        0,
        ["Agree", "Neutral", "Disagree"],
        is_attention_check=True,
        expected_option_index=1,
    )
    add(provider, survey, QuestionType.RATING_SCALE, 1, is_attention_check=True, expected_rating=4)
    add(provider, survey, QuestionType.MULTIPLE_CHOICE, 2, ["Yes", "No"])

    rows = rows_by_order(provider, survey)

    assert rows[0]["is_attention_check"] is True
    assert rows[0]["expected_option_id"] == choice.expected_option_id
    assert rows[0]["expected_answer_label"] == "Neutral"
    assert rows[1]["is_attention_check"] is True
    assert rows[1]["expected_option_id"] is None
    assert rows[1]["expected_answer_label"] == "4"
    assert rows[2]["is_attention_check"] is False
    assert rows[2]["expected_option_id"] is None
    assert rows[2]["expected_answer_label"] == ""


def test_option_dictionaries_are_unchanged(provider, survey):
    add(
        provider,
        survey,
        QuestionType.MULTIPLE_CHOICE,
        0,
        ["Agree", "Disagree"],
        is_attention_check=True,
        expected_option_index=0,
    )

    options = rows_by_order(provider, survey)[0]["options"]

    assert [set(option) for option in options] == [OPTION_KEYS, OPTION_KEYS]
    assert [option["option_text"] for option in options] == ["Agree", "Disagree"]
