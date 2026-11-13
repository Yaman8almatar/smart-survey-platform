"""Analytics dashboard: visible sentiment failure notice (TASK-24, audit A-209)."""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.analysis.views import _question_summaries_view
from apps.core.models import (
    Answer,
    Question,
    Response,
    SentimentAnalysisResult,
    Survey,
    User,
)
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository

NOTICE_BODY = (
    "The answers are saved and counted in the results. "
    "The analysis service could not process them."
)


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey_with_results(failed, completed):
    """Create one response with `failed` FAILED and `completed` COMPLETED open-text results."""
    provider = create_user("provider-view@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-view@example.com", UserType.RESPONDENT)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    response = ResponseRepository().save(Response(survey=survey, respondent=respondent))
    statuses = [AnalysisStatus.FAILED] * failed + [AnalysisStatus.COMPLETED] * completed
    for index, status in enumerate(statuses):
        # One answer per question per response (unique constraint).
        question = QuestionRepository().save(
            Question(
                survey=survey,
                question_text=f"Question {index}?",
                question_type=QuestionType.OPEN_TEXT,
                is_required=True,
                order_index=index,
            )
        )
        answer = ResponseRepository().save_answer(
            Answer(response=response, question=question, answer_value=f"Answer {index}")
        )
        completed_result = status == AnalysisStatus.COMPLETED
        AnalysisRepository().save(
            SentimentAnalysisResult(
                answer=answer,
                status=status,
                sentiment_label=SentimentLabel.POSITIVE if completed_result else None,
                sentiment_score=0.9 if completed_result else None,
                analyzed_at=timezone.now(),
            )
        )
    return provider, survey


def get_dashboard(client, provider, survey):
    client.force_login(provider)
    url = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    return client.get(url).content.decode()


@pytest.mark.django_db
def test_dashboard_shows_singular_failure_notice(client):
    provider, survey = create_survey_with_results(failed=1, completed=1)

    content = get_dashboard(client, provider, survey)

    assert "Sentiment analysis failed for 1 open-text answer." in content
    assert NOTICE_BODY in content
    assert "bi-exclamation-triangle" in content
    assert 'id="sentimentDistributionChart"' in content


@pytest.mark.django_db
def test_dashboard_shows_plural_failure_notice_without_empty_message(client):
    provider, survey = create_survey_with_results(failed=3, completed=0)

    content = get_dashboard(client, provider, survey)

    assert "Sentiment analysis failed for 3 open-text answers." in content
    assert "Sentiment analysis results are not yet available." not in content
    assert 'id="sentimentDistributionChart"' not in content


@pytest.mark.django_db
def test_dashboard_shows_no_failure_notice_when_nothing_failed(client):
    provider, survey = create_survey_with_results(failed=0, completed=1)

    content = get_dashboard(client, provider, survey)

    assert "Sentiment analysis failed" not in content
    assert NOTICE_BODY not in content


@pytest.mark.django_db
def test_dashboard_shows_sentence_case_question_type_not_raw_value(client):
    provider, survey = create_survey_with_results(failed=0, completed=1)

    content = get_dashboard(client, provider, survey)

    assert "Open text" in content
    assert "OPEN_TEXT" not in content


@pytest.mark.django_db
def test_dashboard_text_answer_follows_its_own_direction(client):
    provider, survey = create_survey_with_results(failed=0, completed=1)

    content = get_dashboard(client, provider, survey)

    assert '<div class="text-answer-item" dir="auto">' in content


@pytest.mark.parametrize(
    ("question_type", "label"),
    [
        (QuestionType.MULTIPLE_CHOICE, "Multiple choice"),
        (QuestionType.RATING_SCALE, "Rating scale"),
        (QuestionType.OPEN_TEXT, "Open text"),
    ],
)
def test_question_summaries_view_adds_sentence_case_type_label(question_type, label):
    summary = {"question_id": 7, "question_type": question_type}

    [view] = _question_summaries_view([summary])

    assert view["question_type_label"] == label
    assert view["question_type"] == question_type
