"""FR-11 (TASK-55): schedule and limit on the provider and admin pages, pause and resume."""

import datetime
import re

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Question, Survey, TargetingCriteria, User
from core.enums import AccountStatus, QuestionType, SurveyStatus, UserType
from services.survey_service import SurveyService
from tests.review_helpers import create_admin

pytestmark = pytest.mark.django_db

FIELD_COPY = [
    "Schedule and limit",
    "Opens on",
    "Leave empty to open as soon as an admin approves the survey.",
    "Closes on",
    "The last day respondents can answer. Leave empty to close it yourself.",
    "Close after this many responses",
    "At least 5, because results open at 5 responses. Leave empty for no limit.",
]


def days(n):
    return timezone.localdate() + datetime.timedelta(days=n)


def long_date(day):
    return f"{day.day} {day:%b %Y}"


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def make_survey(provider, status=SurveyStatus.DRAFT, **fields):
    survey = Survey.objects.create(provider=provider, title="Lifecycle", status=status, **fields)
    TargetingCriteria.objects.create(survey=survey)
    Question.objects.create(
        survey=survey,
        question_text="Rate us",
        question_type=QuestionType.RATING_SCALE,
        is_required=True,
        order_index=0,
    )
    return survey


@pytest.fixture
def owner():
    return make_user("provider-lifecycle-view@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def owner_client(client, owner):
    client.force_login(owner)
    return client


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def schedule_rows(html):
    """Return the {label: value} rows of the "Schedule and limit" list of the summary."""
    section = re.search(
        r'<section[^>]*aria-label="Schedule and limit".*?</section>', html, re.S
    ).group(0)
    return dict(
        (dt.strip(), dd.strip())
        for dt, dd in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", section, re.S)
    )


def field(html, name):
    return re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)


# --- Create and edit ------------------------------------------------------------------------


@pytest.mark.parametrize("page", ["create", "edit"])
def test_both_forms_show_the_three_fields_and_their_helps(owner_client, owner, page):
    if page == "create":
        url = reverse("surveys:create_survey")
    else:
        url = reverse("surveys:edit_survey", args=[make_survey(owner).survey_id])

    html = owner_client.get(url).content.decode()

    for text in FIELD_COPY:
        assert text in html
    assert 'type="date"' in field(html, "opens_on")
    assert 'type="date"' in field(html, "closes_on")
    assert 'type="number"' in field(html, "target_responses")


def test_posting_the_create_form_stores_the_settings(owner_client):
    owner_client.post(
        reverse("surveys:create_survey"),
        {
            "title": "Dated",
            "description": "",
            "opens_on": days(1).isoformat(),
            "closes_on": days(9).isoformat(),
            "target_responses": "20",
        },
    )

    survey = Survey.objects.get(title="Dated")
    assert (survey.opens_on, survey.closes_on, survey.target_responses) == (
        days(1),
        days(9),
        20,
    )


def test_the_edit_form_fills_in_and_stores_the_settings(owner_client, owner):
    survey = make_survey(owner, opens_on=days(2), closes_on=days(8), target_responses=30)
    url = reverse("surveys:edit_survey", args=[survey.survey_id])

    html = owner_client.get(url).content.decode()
    assert f'value="{days(2).isoformat()}"' in field(html, "opens_on")
    assert f'value="{days(8).isoformat()}"' in field(html, "closes_on")
    assert 'value="30"' in field(html, "target_responses")

    owner_client.post(url, {"title": "Lifecycle", "description": "", "target_responses": ""})
    survey.refresh_from_db()
    assert (survey.opens_on, survey.closes_on, survey.target_responses) == (None, None, None)


@pytest.mark.parametrize(
    "values, message",
    [
        ({"target_responses": "4"}, "The response limit must be at least 5."),
        ({"closes_on": days(-1).isoformat()}, "The closing date cannot be in the past."),
    ],
)
def test_a_service_error_is_shown_on_the_create_page(owner_client, values, message):
    response = owner_client.post(
        reverse("surveys:create_survey"), {"title": "Bad", "description": "", **values}
    )

    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Survey.objects.filter(title="Bad").exists()


# --- Summary rows -------------------------------------------------------------------------


def test_submit_page_shows_the_schedule_rows_when_set(owner_client, owner):
    survey = make_survey(owner, opens_on=days(3), closes_on=days(12), target_responses=40)

    html = owner_client.get(
        reverse("surveys:submit_for_review", args=[survey.survey_id])
    ).content.decode()

    assert schedule_rows(html) == {
        "Opens": long_date(days(3)),
        "Closes": long_date(days(12)),
        "Response limit": "40 responses",
    }


def test_submit_page_shows_the_schedule_rows_when_empty(owner_client, owner):
    survey = make_survey(owner)

    html = owner_client.get(
        reverse("surveys:submit_for_review", args=[survey.survey_id])
    ).content.decode()

    assert schedule_rows(html) == {
        "Opens": "On approval",
        "Closes": "No closing date",
        "Response limit": "No limit",
    }
    # The rows come after "Who can answer", in their own list.
    assert html.index("Who can answer") < html.index('aria-label="Schedule and limit"')


def test_admin_review_page_shows_the_schedule_rows(client, owner):
    survey = make_survey(owner, closes_on=days(5), target_responses=5)
    SurveyService().submit_for_review(owner, survey.survey_id)
    client.force_login(create_admin("admin-lifecycle-view@example.com"))

    html = client.get(
        reverse("admin_panel:review_survey", args=[survey.survey_id])
    ).content.decode()

    assert schedule_rows(html) == {
        "Opens": "On approval",
        "Closes": long_date(days(5)),
        "Response limit": "5 responses",
    }


# --- Survey list ---------------------------------------------------------------------------


def test_list_shows_the_paused_badge_and_the_resume_button(owner_client, owner):
    make_survey(owner, status=SurveyStatus.PAUSED, closes_on=days(4), target_responses=25)

    html = owner_client.get(reverse("surveys:survey_list")).content.decode()

    assert re.search(r'class="badge text-bg-info">\s*Paused\s*</span>', html)
    assert f"Closes on {long_date(days(4))}" in html
    assert "Closes after 25 responses" in html
    assert re.search(r">\s*Resume\s*</button>", html)
    assert not re.search(r">\s*Pause\s*</button>", html)


def test_list_shows_opens_on_and_the_pause_button_for_a_published_survey(owner_client, owner):
    make_survey(owner, status=SurveyStatus.PUBLISHED, opens_on=days(2))

    html = owner_client.get(reverse("surveys:survey_list")).content.decode()

    assert f"Opens on {long_date(days(2))}" in html
    assert re.search(r">\s*Pause\s*</button>", html)
    assert not re.search(r">\s*Resume\s*</button>", html)
    assert "Closes on" not in html
    assert "Closes after" not in html


def test_list_hides_opens_on_once_the_survey_is_open_or_still_a_draft(owner_client, owner):
    make_survey(owner, status=SurveyStatus.PUBLISHED, opens_on=days(-1))
    make_survey(owner, status=SurveyStatus.DRAFT, opens_on=days(3))

    html = owner_client.get(reverse("surveys:survey_list")).content.decode()

    assert "Opens on" not in html


def test_list_hides_the_date_and_limit_lines_on_a_closed_survey(owner_client, owner):
    make_survey(owner, status=SurveyStatus.CLOSED, closes_on=days(4), target_responses=25)

    html = owner_client.get(reverse("surveys:survey_list")).content.decode()

    assert "Closes on" not in html
    assert "Closes after" not in html


@pytest.mark.parametrize(
    "action, start, end, message",
    [
        ("pause_survey", SurveyStatus.PUBLISHED, SurveyStatus.PAUSED, "Survey paused."),
        ("resume_survey", SurveyStatus.PAUSED, SurveyStatus.PUBLISHED, "Survey resumed."),
    ],
)
def test_pause_and_resume_posts_change_the_state(owner_client, owner, action, start, end, message):
    survey = make_survey(owner, status=start)

    response = owner_client.post(reverse(f"surveys:{action}", args=[survey.survey_id]))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert message in messages_of(response)
    survey.refresh_from_db()
    assert survey.status == end


@pytest.mark.parametrize(
    "action, message",
    [
        ("pause_survey", "Only published surveys can be paused."),
        ("resume_survey", "Only paused surveys can be resumed."),
    ],
)
def test_pause_and_resume_show_the_service_error(owner_client, owner, action, message):
    survey = make_survey(owner, status=SurveyStatus.CLOSED)

    response = owner_client.post(reverse(f"surveys:{action}", args=[survey.survey_id]))

    assert message in messages_of(response)
    survey.refresh_from_db()
    assert survey.status == SurveyStatus.CLOSED


@pytest.mark.parametrize("action", ["pause_survey", "resume_survey"])
def test_get_on_pause_and_resume_is_not_allowed(owner_client, owner, action):
    survey = make_survey(owner, status=SurveyStatus.PUBLISHED)

    response = owner_client.get(reverse(f"surveys:{action}", args=[survey.survey_id]))

    assert response.status_code == 405


# --- Dashboard and report ------------------------------------------------------------------


def test_dashboard_shows_the_paused_card(owner_client, owner):
    make_survey(owner, status=SurveyStatus.PAUSED)
    make_survey(owner, status=SurveyStatus.PAUSED)

    html = owner_client.get(reverse("surveys:provider_dashboard")).content.decode()

    assert re.search(r"<span>Paused</span>\s*<strong>2</strong>", html)
    assert html.count('class="col-sm-6 col-lg-4"') == 6


def test_system_report_shows_the_paused_value(client, owner):
    make_survey(owner, status=SurveyStatus.PAUSED)
    client.force_login(create_admin("admin-lifecycle-report@example.com"))

    html = client.get(reverse("admin_panel:system_reports")).content.decode()

    assert "Draft, pending, published, paused, and closed survey inventory." in html
    assert re.search(r"<span>Paused</span>\s*<strong>1</strong>", html)
