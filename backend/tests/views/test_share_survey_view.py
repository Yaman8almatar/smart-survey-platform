"""FR-10 Part A: the Share button, the share page (W-10) and the QR code download."""

import re

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.core.models import Survey, User
from apps.surveys.qr import qr_svg_bytes
from core.enums import AccountStatus, SurveyStatus, UserType

pytestmark = pytest.mark.django_db

PAGE_COPY = (
    "Share this survey",
    "Anyone with this link can open the survey after they log in or register. "
    "Only respondents who match your targeting can answer it.",
    "Invitation link",
    'data-label-copy="Copy link"',
    'data-label-copied="Link copied"',
    "Select the link and press Ctrl+C to copy it.",
    'alt="QR code for the invitation link"',
    "Download QR code (SVG)",
    "Back to surveys",
)
NOT_TAKING_RESPONSES = (
    "This survey is not taking responses now. People who open the link will be told so."
)
NOT_PUBLISHED_YET = "The invitation link is available once the survey is published."


def _make_user(email, user_type=UserType.SERVICE_PROVIDER):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return _make_user("provider@example.com")


@pytest.fixture
def provider_client(client, provider):
    client.force_login(provider)
    return client


@pytest.fixture
def make_survey(provider):
    def _make_survey(status=SurveyStatus.PUBLISHED, owner=None, title="Campus survey"):
        return Survey.objects.create(provider=owner or provider, title=title, status=status)

    return _make_survey


def _share_url(survey):
    return reverse("surveys:share_survey", args=[survey.survey_id])


def _qr_url(survey):
    return reverse("surveys:share_qr_svg", args=[survey.survey_id])


def _token(survey):
    survey.refresh_from_db()
    return survey.invite_token


def _share_button_count(provider_client, survey):
    content = provider_client.get(reverse("surveys:survey_list")).content.decode()
    return content.count(f'href="{_share_url(survey)}"')


@pytest.mark.parametrize(
    ("status", "shown"),
    [
        (SurveyStatus.PUBLISHED, True),
        (SurveyStatus.PAUSED, True),
        (SurveyStatus.CLOSED, True),
        (SurveyStatus.DRAFT, False),
        (SurveyStatus.PENDING_REVIEW, False),
    ],
)
def test_share_button_shows_only_on_shareable_rows(provider_client, make_survey, status, shown):
    survey = make_survey(status)

    assert _share_button_count(provider_client, survey) == (1 if shown else 0)


def test_share_page_shows_the_copy_the_link_and_the_qr_image(provider_client, make_survey):
    survey = make_survey(title="Library hours")

    response = provider_client.get(_share_url(survey))

    content = response.content.decode()
    assert response.status_code == 200
    for text in PAGE_COPY:
        assert text in content
    assert "Library hours" in content
    assert f"/?invite={_token(survey)}" in content
    assert re.search(r'<img\s+src="data:image/svg\+xml', content)
    assert NOT_TAKING_RESPONSES not in content


@pytest.mark.parametrize("status", (SurveyStatus.PAUSED, SurveyStatus.CLOSED))
def test_paused_or_closed_survey_shows_the_not_taking_responses_line(
    provider_client, make_survey, status
):
    survey = make_survey(status)

    content = provider_client.get(_share_url(survey)).content.decode()

    assert NOT_TAKING_RESPONSES in content


@pytest.mark.parametrize("status", (SurveyStatus.DRAFT, SurveyStatus.PENDING_REVIEW))
def test_unpublished_survey_redirects_to_the_list_with_the_message(
    provider_client, make_survey, status
):
    survey = make_survey(status)

    response = provider_client.get(_share_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert [str(m) for m in get_messages(response.wsgi_request)] == [NOT_PUBLISHED_YET]
    assert _token(survey) is None


@pytest.mark.parametrize("url", (_share_url, _qr_url))
def test_another_provider_is_redirected_and_no_token_is_stored(client, make_survey, url):
    survey = make_survey()
    client.force_login(_make_user("other@example.com"))

    response = client.get(url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert _token(survey) is None


@pytest.mark.parametrize("url", (_share_url, _qr_url))
def test_anonymous_visitor_goes_to_log_in(client, make_survey, url):
    survey = make_survey()

    response = client.get(url(survey))

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert _token(survey) is None


def test_qr_download_is_an_svg_attachment_of_the_link(provider_client, make_survey, settings):
    survey = make_survey()

    response = provider_client.get(_qr_url(survey))

    link = f"{settings.APP_PUBLIC_URL}/?invite={_token(survey)}"
    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert response["Content-Disposition"] == (
        f'attachment; filename="survey-{survey.survey_id}-invitation-qr.svg"'
    )
    assert response.content == qr_svg_bytes(link)
    assert response.content.startswith(b"<?xml")


def test_token_stays_the_same_across_both_pages(provider_client, make_survey):
    survey = make_survey()

    provider_client.get(_share_url(survey))
    first = _token(survey)
    provider_client.get(_qr_url(survey))
    provider_client.get(_share_url(survey))

    assert first is not None
    assert _token(survey) == first


def test_share_page_answers_get_only(provider_client, make_survey):
    survey = make_survey()

    assert provider_client.post(_share_url(survey)).status_code == 405
