"""FR-04 Part 1 (TASK-41): attention-check rules, the publish refusal and delete_survey (P-06)."""

import pytest

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import NotEditable, ValidationError
from services.question_service import QuestionService
from services.survey_service import SurveyService
from tests.review_helpers import publish_through_review

pytestmark = pytest.mark.django_db


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return make_user("provider-attention@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    survey = Survey.objects.create(provider=provider, title="Attention")
    TargetingCriteria.objects.create(survey=survey, regions=[], gender=None)
    return survey


def add(provider, survey, question_type=QuestionType.MULTIPLE_CHOICE, **kwargs):
    kwargs.setdefault("is_required", False)
    options = kwargs.pop("options", ["A", "B", "C"])
    if question_type != QuestionType.MULTIPLE_CHOICE:
        options = None
    return QuestionService().add_question_with_options(
        provider,
        survey.survey_id,
        "Choose C to show you are reading",
        question_type,
        kwargs.pop("is_required"),
        0,
        options=options,
        **kwargs,
    )


def test_multiple_choice_attention_check_stores_the_option_at_the_index(provider, survey):
    question = add(provider, survey, is_attention_check=True, expected_option_index=2)

    stored = Question.objects.get(pk=question.pk)
    assert stored.is_attention_check is True
    assert stored.expected_option.option_text == "C"
    assert stored.expected_rating is None
    assert stored.is_required is True


def test_rating_attention_check_stores_the_expected_rating(provider, survey):
    question = add(
        provider,
        survey,
        QuestionType.RATING_SCALE,
        is_attention_check=True,
        expected_rating=5,
    )

    stored = Question.objects.get(pk=question.pk)
    assert stored.is_attention_check is True
    assert stored.expected_rating == 5
    assert stored.expected_option is None
    assert stored.is_required is True


def test_open_text_cannot_be_an_attention_check(provider, survey):
    with pytest.raises(ValidationError, match="^Attention checks work on multiple-choice and rating questions.$"):
        add(provider, survey, QuestionType.OPEN_TEXT, is_attention_check=True)

    assert not Question.objects.filter(survey=survey).exists()


def test_a_survey_holds_at_most_two_attention_checks(provider, survey):
    add(provider, survey, is_attention_check=True, expected_option_index=0)
    add(provider, survey, QuestionType.RATING_SCALE, is_attention_check=True, expected_rating=1)

    with pytest.raises(ValidationError, match="^This survey already has 2 attention checks.$"):
        add(provider, survey, is_attention_check=True, expected_option_index=1)

    assert Question.objects.filter(survey=survey).count() == 2


@pytest.mark.parametrize(
    "question_type, expected",
    [
        (QuestionType.MULTIPLE_CHOICE, {}),
        (QuestionType.RATING_SCALE, {}),
        (QuestionType.MULTIPLE_CHOICE, {"expected_rating": 3}),
        (QuestionType.RATING_SCALE, {"expected_option_index": 0}),
    ],
)
def test_an_attention_check_needs_its_kind_of_expected_answer(
    provider, survey, question_type, expected
):
    with pytest.raises(ValidationError, match="^Choose the expected answer.$"):
        add(provider, survey, question_type, is_attention_check=True, **expected)

    assert not Question.objects.filter(survey=survey).exists()


@pytest.mark.parametrize("index", [-1, 3, "1"])
def test_expected_option_index_must_be_inside_the_options(provider, survey, index):
    with pytest.raises(ValidationError, match="^The expected answer must be one of the options.$"):
        add(provider, survey, is_attention_check=True, expected_option_index=index)

    assert not Question.objects.filter(survey=survey).exists()


@pytest.mark.parametrize("rating", [0, 6, "5"])
def test_expected_rating_must_be_from_1_to_5(provider, survey, rating):
    with pytest.raises(ValidationError, match="^The expected rating must be from 1 to 5.$"):
        add(
            provider,
            survey,
            QuestionType.RATING_SCALE,
            is_attention_check=True,
            expected_rating=rating,
        )


@pytest.mark.parametrize(
    "question_type, expected",
    [
        (QuestionType.MULTIPLE_CHOICE, {"expected_option_index": 0}),
        (QuestionType.RATING_SCALE, {"expected_rating": 4}),
    ],
)
def test_a_plain_question_takes_no_expected_answer(provider, survey, question_type, expected):
    with pytest.raises(ValidationError, match="^Only an attention check has an expected answer.$"):
        add(provider, survey, question_type, **expected)

    assert not Question.objects.filter(survey=survey).exists()


def test_update_question_keeps_an_attention_check_required(provider, survey):
    question = add(provider, survey, is_attention_check=True, expected_option_index=0)

    QuestionService().update_question(provider, question.question_id, "New text", False, 1)

    stored = Question.objects.get(pk=question.pk)
    assert stored.question_text == "New text"
    assert stored.is_required is True


def test_update_question_still_changes_a_plain_question_to_optional(provider, survey):
    question = add(provider, survey, is_required=True)

    QuestionService().update_question(provider, question.question_id, "Text", False, 0)

    assert Question.objects.get(pk=question.pk).is_required is False


def test_submit_for_review_refuses_an_attention_check_whose_option_was_deleted(
    provider, survey
):
    question = add(provider, survey, is_attention_check=True, expected_option_index=2)
    QuestionOption.objects.filter(question=question, option_text="C").delete()

    with pytest.raises(ValidationError, match="^An attention check needs its expected answer.$"):
        SurveyService().submit_for_review(provider, survey.survey_id)

    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.DRAFT


def test_publish_accepts_attention_checks_with_their_expected_answers(provider, survey):
    add(provider, survey, is_attention_check=True, expected_option_index=2)
    add(provider, survey, QuestionType.RATING_SCALE, is_attention_check=True, expected_rating=4)

    publish_through_review(provider, survey.survey_id)

    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.PUBLISHED


def add_response(survey):
    respondent = make_user(f"respondent-delete-{survey.pk}@example.com", UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=respondent, age=30, gender=Gender.MALE, region="DAMASCUS", interests=["SPORTS"]
    )
    Response.objects.create(survey=survey, respondent=respondent)


def test_delete_survey_refuses_a_survey_that_has_responses(provider, survey):
    Survey.objects.filter(pk=survey.pk).update(status=SurveyStatus.CLOSED)
    add_response(survey)

    with pytest.raises(NotEditable, match="^A survey that has responses cannot be deleted.$"):
        SurveyService().delete_survey(provider, survey.survey_id)

    assert Survey.objects.filter(pk=survey.pk).exists()


@pytest.mark.parametrize("status", [SurveyStatus.DRAFT, SurveyStatus.CLOSED])
def test_delete_survey_deletes_a_survey_without_responses(provider, survey, status):
    Survey.objects.filter(pk=survey.pk).update(status=status)

    SurveyService().delete_survey(provider, survey.survey_id)

    assert not Survey.objects.filter(pk=survey.pk).exists()
