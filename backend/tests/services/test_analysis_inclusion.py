"""FR-04 Part 2 (TASK-42): analytics count included responses only; the lock counts all."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    Response,
    SentimentAnalysisResult,
    Survey,
    User,
)
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from services.analysis_service import AnalysisService

pytestmark = pytest.mark.django_db


class FakeClient:
    model_id = "org/sentiment-model"

    def analyze_sentiment(self, text):
        raise AssertionError("Reading results must not call the analysis client.")


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def setup():
    """A survey with a choice, a rating, an attention choice and two open texts."""
    provider = make_user("provider-inclusion@example.com", UserType.SERVICE_PROVIDER)
    survey = Survey.objects.create(provider=provider, title="Inclusion")
    questions = {}
    for index, (key, question_type, attention) in enumerate(
        [
            ("choice", QuestionType.MULTIPLE_CHOICE, False),
            ("rating", QuestionType.RATING_SCALE, False),
            ("attention", QuestionType.MULTIPLE_CHOICE, True),
            ("text", QuestionType.OPEN_TEXT, False),
            ("second_text", QuestionType.OPEN_TEXT, False),
        ]
    ):
        questions[key] = Question.objects.create(
            survey=survey,
            question_text=key,
            question_type=question_type,
            order_index=index,
            is_attention_check=attention,
        )
    for key in ("choice", "attention"):
        for option_index, text in enumerate(["Yes", "No"]):
            QuestionOption.objects.create(
                question=questions[key], option_text=text, order_index=option_index
            )
    return provider, survey, questions


def add_response(survey, questions, option, rating, label, second_status, excluded=False):
    index = Response.objects.count()
    respondent = make_user(f"respondent-inclusion-{index}@example.com", UserType.RESPONDENT)
    response = Response.objects.create(survey=survey, respondent=respondent, is_excluded=excluded)
    options = list(questions["choice"].options.order_by("order_index"))
    Answer.objects.create(
        response=response, question=questions["choice"], selected_option=options[option]
    )
    Answer.objects.create(response=response, question=questions["rating"], rating_value=rating)
    Answer.objects.create(
        response=response,
        question=questions["attention"],
        selected_option=questions["attention"].options.first(),
    )
    text = Answer.objects.create(
        response=response, question=questions["text"], answer_value=f"Text {index}"
    )
    second = Answer.objects.create(
        response=response, question=questions["second_text"], answer_value=f"More {index}"
    )
    SentimentAnalysisResult.objects.create(
        answer=text,
        status=AnalysisStatus.COMPLETED,
        sentiment_label=label,
        sentiment_score=0.9,
        analyzed_at=timezone.now(),
    )
    SentimentAnalysisResult.objects.create(
        answer=second,
        status=second_status,
        error_code="payment_required" if second_status == AnalysisStatus.FAILED else "",
    )
    return response


def results(provider, survey):
    return AnalysisService(analyzer=FakeClient()).get_survey_results(provider, survey.survey_id)


def summary(result, question):
    return next(
        item for item in result["question_summaries"] if item["question_id"] == question.question_id
    )


def test_an_excluded_response_leaves_the_summaries_and_counts(setup):
    provider, survey, questions = setup
    for _ in range(5):
        add_response(survey, questions, 0, 5, SentimentLabel.POSITIVE, AnalysisStatus.SKIPPED)
    add_response(
        survey, questions, 1, 1, SentimentLabel.NEGATIVE, AnalysisStatus.FAILED, excluded=True
    )
    add_response(
        survey, questions, 1, 2, SentimentLabel.NEUTRAL, AnalysisStatus.PENDING, excluded=True
    )

    result = results(provider, survey)

    assert result["response_count"] == 7
    assert result["included_count"] == 5
    assert result["positive_count"] == 5
    assert result["neutral_count"] == 0
    assert result["negative_count"] == 0
    assert result["positive_rate"] == 1
    assert result["skipped_count"] == 5
    assert result["failed_count"] == 0
    assert result["waiting_count"] == 0
    assert result["failed_reasons"] == []
    assert summary(result, questions["choice"])["values"] == [5, 0]
    assert summary(result, questions["rating"])["values"] == [0, 0, 0, 0, 5]
    text_summary = summary(result, questions["text"])
    assert text_summary["text_answer_total"] == 5
    assert all(int(text.split()[1]) < 5 for text in text_summary["text_answers"])


def test_with_no_exclusion_every_response_counts(setup):
    provider, survey, questions = setup
    for _ in range(4):
        add_response(survey, questions, 0, 5, SentimentLabel.POSITIVE, AnalysisStatus.SKIPPED)
    add_response(survey, questions, 1, 1, SentimentLabel.NEGATIVE, AnalysisStatus.FAILED)

    result = results(provider, survey)

    assert result["included_count"] == result["response_count"] == 5
    assert result["negative_count"] == 1
    assert result["failed_count"] == 1
    assert summary(result, questions["choice"])["values"] == [4, 1]


def test_an_attention_question_is_absent_from_question_summaries(setup):
    provider, survey, questions = setup
    for _ in range(5):
        add_response(survey, questions, 0, 5, SentimentLabel.POSITIVE, AnalysisStatus.SKIPPED)

    result = results(provider, survey)

    ids = [item["question_id"] for item in result["question_summaries"]]
    assert questions["attention"].question_id not in ids
    assert ids == [
        questions[key].question_id for key in ("choice", "rating", "text", "second_text")
    ]


def test_response_count_and_the_lock_ignore_exclusion(setup):
    provider, survey, questions = setup
    for index in range(5):
        add_response(
            survey,
            questions,
            0,
            5,
            SentimentLabel.POSITIVE,
            AnalysisStatus.FAILED,
            excluded=index < 4,
        )

    result = results(provider, survey)

    assert result["locked"] is False
    assert result["response_count"] == 5
    assert result["included_count"] == 1
    assert result["failed_count"] == 1
    # retry_failed stays on submitted responses: no lock error, every FAILED row is reset.
    assert AnalysisService(analyzer=FakeClient()).retry_failed(provider, survey.survey_id) == 5


def test_analysis_overdue_watches_every_row(setup):
    provider, survey, questions = setup
    for _ in range(5):
        add_response(survey, questions, 0, 5, SentimentLabel.POSITIVE, AnalysisStatus.SKIPPED)
    late = add_response(
        survey, questions, 0, 5, SentimentLabel.POSITIVE, AnalysisStatus.PENDING, excluded=True
    )
    Response.objects.filter(pk=late.pk).update(submitted_at=timezone.now() - timedelta(hours=1))

    result = results(provider, survey)

    assert result["waiting_count"] == 0
    assert result["analysis_overdue"] is True
