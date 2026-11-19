"""P-20 (D-168): a survey's results stay closed until it has 5 responses.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE.
"""

import pytest
from django.utils import timezone

from apps.core.models import Answer, Question, Response, SentimentAnalysisResult, Survey, User
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from core.exceptions import UnauthorizedAction, ValidationError
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services.analysis_service import AnalysisService
from services.disclosure import MIN_GROUP_SIZE


class FakeClient:
    model_id = "org/sentiment-model"

    def analyze_sentiment(self, text):
        raise AssertionError("Reading results must not call the analysis client.")


class ResponseRepositoryThatMustNotCount(ResponseRepository):
    def find_by_survey_id(self, survey_id):
        raise AssertionError("Responses were counted before the owner check.")


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey_with_responses(count):
    """Create a survey with one open-text question and `count` analysed answers."""
    provider = create_user("provider-lock@example.com", UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Any comments?",
            question_type=QuestionType.OPEN_TEXT,
            is_required=True,
            order_index=0,
        )
    )
    for index in range(count):
        respondent = create_user(f"respondent-lock-{index}@example.com", UserType.RESPONDENT)
        response = ResponseRepository().save(Response(survey=survey, respondent=respondent))
        answer = ResponseRepository().save_answer(
            Answer(response=response, question=question, answer_value=f"Answer {index}")
        )
        AnalysisRepository().save(
            SentimentAnalysisResult(
                answer=answer,
                status=AnalysisStatus.COMPLETED,
                sentiment_label=SentimentLabel.POSITIVE,
                sentiment_score=0.9,
                analyzed_at=timezone.now(),
            )
        )
    return provider, survey


def test_threshold_is_the_disclosure_constant():
    assert MIN_GROUP_SIZE == 5


@pytest.mark.django_db
def test_four_responses_return_only_the_locked_dictionary():
    provider, survey = create_survey_with_responses(4)

    results = AnalysisService(analyzer=FakeClient()).get_survey_results(
        provider, survey.survey_id
    )

    assert results == {
        "survey_id": survey.survey_id,
        "response_count": 4,
        "locked": True,
        "min_responses": 5,
    }


@pytest.mark.django_db
def test_locked_call_reads_no_answers_results_or_questions(django_assert_max_num_queries):
    provider, survey = create_survey_with_responses(4)
    service = AnalysisService(analyzer=FakeClient())

    # Two queries: the survey for the owner check and the COUNT of its responses.
    # The answers, sentiment results and questions are never queried.
    with django_assert_max_num_queries(2) as captured:
        service.get_survey_results(provider, survey.survey_id)

    sql = " ".join(query["sql"] for query in captured.captured_queries)
    assert len(captured.captured_queries) == 2
    assert '"answers"' not in sql
    assert '"sentiment_analysis_results"' not in sql
    assert '"questions"' not in sql


@pytest.mark.django_db
def test_five_responses_open_the_results():
    provider, survey = create_survey_with_responses(5)

    results = AnalysisService(analyzer=FakeClient()).get_survey_results(
        provider, survey.survey_id
    )

    assert results["locked"] is False
    assert results["min_responses"] == 5
    assert results["response_count"] == 5
    assert results["positive_count"] == 5
    assert results["question_summaries"][0]["text_answer_total"] == 5


def mark_failed(survey, count):
    """Turn `count` of the survey's results into FAILED ones."""
    ids = list(
        SentimentAnalysisResult.objects.filter(answer__response__survey=survey)
        .order_by("result_id")
        .values_list("result_id", flat=True)[:count]
    )
    SentimentAnalysisResult.objects.filter(result_id__in=ids).update(
        status=AnalysisStatus.FAILED, error_code="payment_required"
    )


@pytest.mark.django_db
def test_retry_failed_is_refused_while_results_are_locked():
    provider, survey = create_survey_with_responses(4)
    mark_failed(survey, 2)

    with pytest.raises(ValidationError, match="Results open at 5 responses."):
        AnalysisService(analyzer=FakeClient()).retry_failed(provider, survey.survey_id)

    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.FAILED).count() == 2


@pytest.mark.django_db
def test_retry_failed_returns_the_count_when_results_are_open():
    provider, survey = create_survey_with_responses(5)
    mark_failed(survey, 2)

    reset = AnalysisService(analyzer=FakeClient()).retry_failed(
        provider, survey.survey_id
    )

    assert reset == 2
    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.FAILED).count() == 0


@pytest.mark.django_db
def test_retry_failed_checks_the_owner_before_any_count():
    _, survey = create_survey_with_responses(1)
    other_provider = create_user("other-retry-lock@example.com", UserType.SERVICE_PROVIDER)
    service = AnalysisService(
        response_repository=ResponseRepositoryThatMustNotCount(),
        analyzer=FakeClient(),
    )

    with pytest.raises(UnauthorizedAction):
        service.retry_failed(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_another_provider_is_refused_before_any_count():
    _, survey = create_survey_with_responses(1)
    other_provider = create_user("other-provider-lock@example.com", UserType.SERVICE_PROVIDER)
    service = AnalysisService(
        response_repository=ResponseRepositoryThatMustNotCount(),
        analyzer=FakeClient(),
    )

    with pytest.raises(UnauthorizedAction):
        service.get_survey_results(other_provider, survey.survey_id)
