"""FR-12 (TASK-54): the admin's review list, review page, approve and reject."""

from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Question, QuestionOption, Survey, TargetingCriteria, User
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from services.survey_service import SurveyService
from tests.review_helpers import create_admin

pytestmark = pytest.mark.django_db


def make_user(email, user_type, name="User"):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name=name,
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return make_user("provider-views@example.com", UserType.SERVICE_PROVIDER, "Lina Provider")


@pytest.fixture
def admin_client(client):
    client.force_login(create_admin("admin-views@example.com"))
    return client


def pending_survey(provider, title="Bus routes", description="Routes in the city."):
    survey = Survey.objects.create(provider=provider, title=title, description=description)
    Question.objects.create(
        survey=survey,
        question_text="How was it?",
        question_type=QuestionType.OPEN_TEXT,
        is_required=False,
        order_index=0,
    )
    choice = Question.objects.create(
        survey=survey,
        question_text='Choose "Blue" to show you are reading',
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=1,
        is_attention_check=True,
    )
    QuestionOption.objects.create(question=choice, option_text="Red", order_index=0)
    blue = QuestionOption.objects.create(question=choice, option_text="Blue", order_index=1)
    choice.expected_option = blue
    choice.save()
    TargetingCriteria.objects.create(survey=survey, gender=Gender.FEMALE, regions=["HOMS"])
    SurveyService().submit_for_review(provider, survey.survey_id)
    return Survey.objects.get(pk=survey.pk)


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def addresses(survey_id):
    return [
        ("get", reverse("admin_panel:review_queue")),
        ("get", reverse("admin_panel:review_survey", args=[survey_id])),
        ("post", reverse("admin_panel:approve_survey", args=[survey_id])),
        ("post", reverse("admin_panel:reject_survey", args=[survey_id])),
    ]


@pytest.mark.parametrize("who", ["provider", "anonymous"])
def test_only_an_admin_reaches_the_review_pages(client, provider, who):
    survey = pending_survey(provider)
    if who == "provider":
        client.force_login(provider)

    for method, url in addresses(survey.survey_id):
        response = getattr(client, method)(url, {"reason": "No."})
        assert response.status_code == 302, url
        assert response.url == reverse("users:login"), url

    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.PENDING_REVIEW


def test_the_list_shows_pending_surveys_oldest_first(admin_client, provider):
    newer = pending_survey(provider, "Newer survey")
    older = pending_survey(provider, "Older survey")
    now = timezone.now()
    Survey.objects.filter(pk=older.pk).update(submitted_at=now - timedelta(days=3))
    Survey.objects.filter(pk=newer.pk).update(submitted_at=now - timedelta(days=1))

    response = admin_client.get(reverse("admin_panel:review_queue"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Surveys waiting for review" in html
    assert "Oldest first. A survey is published only after you approve it." in html
    for column in ("Survey", "Provider", "Submitted", "Questions"):
        assert f"<th>{column}</th>" in html
    assert html.index("Older survey") < html.index("Newer survey")
    assert "Lina Provider" in html
    assert "provider-views@example.com" in html
    assert "<td>2</td>" in html
    assert reverse("admin_panel:review_survey", args=[older.survey_id]) in html


def test_the_list_without_pending_surveys_shows_the_empty_text(admin_client):
    html = admin_client.get(reverse("admin_panel:review_queue")).content.decode()

    assert "No survey is waiting for review." in html


def test_the_review_page_shows_the_survey_its_targeting_and_questions(admin_client, provider):
    survey = pending_survey(provider)
    day = timezone.localtime(survey.submitted_at)

    response = admin_client.get(reverse("admin_panel:review_survey", args=[survey.survey_id]))

    assert response.status_code == 200
    html = response.content.decode()
    assert f"Submitted on {day.day} {day:%b} {day.year} by Lina Provider, provider-views@example.com." in html
    assert "Routes in the city." in html
    assert "<dt>Gender</dt><dd>Female</dd>" in html
    assert "<dt>Governorates</dt><dd>Homs</dd>" in html
    assert "<dt>Interests</dt><dd>Any</dd>" in html
    assert "Edit targeting" not in html
    assert "1. How was it?" in html
    assert "Open text - Optional" in html
    assert "Multiple choice - Required" in html
    assert "Red" in html and "Blue" in html
    assert "Expected answer: <strong>Blue</strong>" in html
    assert "Approve and publish" in html
    assert "Reject and return" in html
    assert 'maxlength="1000"' in html
    assert "Reason for the provider" in html
    assert "Back to the review list" in html


def test_the_review_page_without_description(admin_client, provider):
    survey = pending_survey(provider, description="")

    html = admin_client.get(
        reverse("admin_panel:review_survey", args=[survey.survey_id])
    ).content.decode()

    assert "No description." in html


def test_the_review_page_of_a_survey_no_longer_pending_goes_back_to_the_list(
    admin_client, provider
):
    survey = pending_survey(provider)
    Survey.objects.filter(pk=survey.pk).update(status=SurveyStatus.DRAFT)

    response = admin_client.get(reverse("admin_panel:review_survey", args=[survey.survey_id]))

    assert response.url == reverse("admin_panel:review_queue")
    assert messages_of(response) == ["This survey is no longer waiting for review."]


@pytest.mark.parametrize("name", ["approve_survey", "reject_survey"])
def test_approve_and_reject_refuse_get(admin_client, provider, name):
    survey = pending_survey(provider)

    response = admin_client.get(reverse(f"admin_panel:{name}", args=[survey.survey_id]))

    assert response.status_code == 405


def test_approve_publishes_the_survey(admin_client, provider):
    survey = pending_survey(provider)

    response = admin_client.post(reverse("admin_panel:approve_survey", args=[survey.survey_id]))

    assert response.url == reverse("admin_panel:review_queue")
    assert messages_of(response) == ["Survey approved and published."]
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.PUBLISHED


def test_approve_of_a_survey_no_longer_pending_shows_its_message(admin_client, provider):
    survey = pending_survey(provider)
    url = reverse("admin_panel:approve_survey", args=[survey.survey_id])
    admin_client.post(url)

    response = admin_client.post(url)

    assert response.url == reverse("admin_panel:review_queue")
    assert "This survey is no longer waiting for review." in messages_of(response)


def test_a_blank_reason_keeps_the_survey_pending(admin_client, provider):
    survey = pending_survey(provider)

    response = admin_client.post(
        reverse("admin_panel:reject_survey", args=[survey.survey_id]), {"reason": "   "}
    )

    assert response.url == reverse("admin_panel:review_survey", args=[survey.survey_id])
    assert messages_of(response) == ["Write a reason for the provider."]
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.PENDING_REVIEW


def test_a_reason_returns_the_survey_to_the_provider(admin_client, provider):
    survey = pending_survey(provider)

    response = admin_client.post(
        reverse("admin_panel:reject_survey", args=[survey.survey_id]),
        {"reason": "Question 1 is leading."},
    )

    assert response.url == reverse("admin_panel:review_queue")
    assert messages_of(response) == ["Survey returned to the provider."]
    stored = Survey.objects.get(pk=survey.pk)
    assert stored.status == SurveyStatus.DRAFT
    assert stored.rejection_reason == "Question 1 is leading."


def test_the_dashboard_card_shows_the_waiting_count(admin_client, provider):
    pending_survey(provider, "One")
    pending_survey(provider, "Two")

    html = admin_client.get(reverse("admin_panel:admin_dashboard")).content.decode()

    assert "Survey review" in html
    assert "Approve or reject surveys before they are published." in html
    assert "Review surveys" in html
    assert '<span class="badge text-bg-light ms-1">2</span>' in html


def test_the_nav_link_is_marked_current_on_the_review_pages(admin_client, provider):
    survey = pending_survey(provider)
    queue_url = reverse("admin_panel:review_queue")

    for url in (queue_url, reverse("admin_panel:review_survey", args=[survey.survey_id])):
        html = admin_client.get(url).content.decode()
        assert f' aria-current="page"\n                                    href="{queue_url}"' in html


def test_the_system_report_shows_pending_review(admin_client, provider):
    pending_survey(provider)

    html = admin_client.get(reverse("admin_panel:system_reports")).content.decode()

    assert "Draft, pending, published, paused, and closed survey inventory." in html
    assert "<span>Pending review</span>" in html
    assert html.index("<span>Draft</span>") < html.index("<span>Pending review</span>")
    assert html.index("<span>Pending review</span>") < html.index("<span>Published</span>")
