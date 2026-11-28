"""P-20 (D-168): the analytics page shows a locked state below 5 responses.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE.
"""

import pytest
from django.urls import reverse

from apps.core.models import Answer, Question, Response, Survey, User
from core.enums import AccountStatus, QuestionType, SurveyStatus, UserType
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository

HEADING = "Results open at 5 responses"
NO_RESPONSES = "No responses have been submitted for this survey yet."


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey_with_responses(count, status=SurveyStatus.PUBLISHED):
    """Create a survey with one open-text question answered `count` times."""
    provider = create_user("provider-lock-view@example.com", UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description", status=status)
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
        respondent = create_user(
            f"respondent-lock-view-{index}@example.com", UserType.RESPONDENT
        )
        response = ResponseRepository().save(Response(survey=survey, respondent=respondent))
        ResponseRepository().save_answer(
            Answer(response=response, question=question, answer_value=f"Secret answer {index}")
        )
    return provider, survey


def get_dashboard(client, provider, survey):
    client.force_login(provider)
    url = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    return client.get(url).content.decode()


@pytest.mark.django_db
def test_three_responses_show_the_locked_card_and_nothing_else(client):
    provider, survey = create_survey_with_responses(3)

    content = get_dashboard(client, provider, survey)

    assert HEADING in content
    assert (
        "This survey has 3 responses. Results stay hidden until at least 5 people "
        "have answered, so no answer can be traced back to one person."
    ) in content
    assert "Secret answer" not in content
    assert "Any comments?" not in content
    assert 'class="metric-card"' not in content
    assert "Positive rate" not in content
    assert "<canvas" not in content
    assert "question-chart-data" not in content
    assert "new Chart(" not in content


@pytest.mark.django_db
def test_one_response_uses_the_singular(client):
    provider, survey = create_survey_with_responses(1)

    content = get_dashboard(client, provider, survey)

    assert "This survey has 1 response. Results stay hidden" in content


@pytest.mark.django_db
def test_closed_survey_with_two_responses_shows_the_closed_line(client):
    provider, survey = create_survey_with_responses(2, status=SurveyStatus.CLOSED)

    content = get_dashboard(client, provider, survey)

    assert HEADING in content
    assert (
        "This survey closed with 2 responses. Its results stay hidden because "
        "fewer than 5 people answered."
    ) in content
    assert "Secret answer" not in content


@pytest.mark.django_db
def test_zero_responses_keep_the_empty_line(client):
    provider, survey = create_survey_with_responses(0)

    content = get_dashboard(client, provider, survey)

    assert HEADING in content
    assert NO_RESPONSES in content
    assert "This survey has" not in content


@pytest.mark.django_db
def test_five_responses_show_the_results(client):
    provider, survey = create_survey_with_responses(5)

    content = get_dashboard(client, provider, survey)

    assert HEADING not in content
    assert "Secret answer 3" in content
    assert 'class="metric-card"' in content
