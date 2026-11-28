"""FR-12 (TASK-54): what the provider sees while a survey waits for review or after a rejection."""

import pytest
from django.contrib.messages import get_messages
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.models import Question, Survey, TargetingCriteria, User
from core.enums import AccountStatus, QuestionType, SurveyStatus, UserType
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService
from tests.review_helpers import create_admin

pytestmark = pytest.mark.django_db


@pytest.fixture
def provider():
    return User.objects.create_user(
        email="provider-status@example.com",
        password="strong-password",
        name="Provider",
        user_type=UserType.SERVICE_PROVIDER,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider_client(client, provider):
    client.force_login(provider)
    return client


def ready_draft(provider, title="Bus routes"):
    survey = Survey.objects.create(provider=provider, title=title, description="D")
    Question.objects.create(
        survey=survey,
        question_text="How was it?",
        question_type=QuestionType.OPEN_TEXT,
        is_required=True,
        order_index=0,
    )
    TargetingCriteria.objects.create(survey=survey)
    return survey


def submitted(provider, title="Bus routes"):
    survey = ready_draft(provider, title)
    SurveyService().submit_for_review(provider, survey.survey_id)
    return survey


def list_html(client):
    return client.get(reverse("surveys:survey_list")).content.decode()


def test_a_pending_row_shows_its_badge_and_no_actions(provider_client, provider):
    survey = submitted(provider)

    html = list_html(provider_client)

    assert '<span class="badge text-bg-warning">' in html
    assert "Pending review" in html
    assert "Waiting for review" in html
    assert reverse("surveys:edit_survey", args=[survey.survey_id]) not in html
    assert reverse("surveys:delete_survey", args=[survey.survey_id]) not in html
    assert reverse("surveys:submit_for_review", args=[survey.survey_id]) not in html


def test_a_draft_row_offers_submit_for_review(provider_client, provider):
    survey = ready_draft(provider)

    html = list_html(provider_client)

    assert f'href="{reverse("surveys:submit_for_review", args=[survey.survey_id])}"' in html
    assert "Submit for review" in html
    assert "Waiting for review" not in html


def test_a_returned_draft_shows_the_date_and_the_reason(provider_client, provider):
    survey = submitted(provider)
    SurveyReviewService().reject(create_admin(), survey.survey_id, "Question 1 is leading.")
    reviewed_at = Survey.objects.get(pk=survey.pk).reviewed_at
    day = timezone.localtime(reviewed_at)

    html = list_html(provider_client)

    expected = f"Returned by the admin on {day.day} {day:%b} {day.year}: Question 1 is leading."
    assert expected in html
    assert reverse("surveys:edit_survey", args=[survey.survey_id]) in html


def test_the_reason_is_shown_as_text(provider_client, provider):
    survey = submitted(provider)
    SurveyReviewService().reject(create_admin(), survey.survey_id, "<b>x</b>")

    html = list_html(provider_client)

    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html


def test_the_dashboard_counts_pending_surveys(provider_client, provider):
    submitted(provider, "One")
    submitted(provider, "Two")
    ready_draft(provider, "Draft")

    response = provider_client.get(reverse("surveys:provider_dashboard"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "<span>Pending review</span>" in html
    assert "<strong>2</strong>" in html
    assert html.count('class="col-sm-6 col-lg-4"') == 6


def test_post_to_the_submit_address_moves_the_survey_to_pending(provider_client, provider):
    survey = ready_draft(provider)

    response = provider_client.post(
        reverse("surveys:submit_for_review", args=[survey.survey_id])
    )

    assert response.status_code == 302
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        "Survey submitted for review."
    ]
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.PENDING_REVIEW


def test_the_old_publish_address_is_gone(provider_client, provider):
    survey = ready_draft(provider)

    response = provider_client.post(f"/surveys/{survey.survey_id}/publish/")

    assert response.status_code == 404
    with pytest.raises(NoReverseMatch):
        reverse("surveys:publish_survey", args=[survey.survey_id])
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.DRAFT
