"""TASK-49 (FR-07, FR-09, board W-07): the responses list, one response, and its include or exclude.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import html
import itertools
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from apps.analysis import response_views
from apps.analysis.views import QUALITY_FLAG_ORDER
from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    Response,
    ResponseQuality,
    SentimentAnalysisResult,
    Survey,
    User,
)
from core.enums import (
    AccountStatus,
    AnalysisStatus,
    QuestionType,
    SentimentLabel,
    SurveyStatus,
    UserType,
)
from tests.views.test_quality_panel_view import MEANINGS, NAMES

pytestmark = pytest.mark.django_db

SUBMITTED = timezone.make_aware(datetime(2026, 11, 18, 14, 37))
SECRET_NAME = "Rania Haddad"
SECRET_EMAIL = "rania.secret@example.com"
DEVICE_HASH = "a1b2c3d4" * 8
LOCKED_HEADING = "Results open at 5 responses"
SUBTITLE = "Each response is shown under a number. The platform never shows who answered."
BEFORE_CHECKS = (
    "This response was collected before quality checks. It has no score and stays included."
)
KEPT = "Excluded responses are kept and can be included again at any time."
TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "apps/analysis/templates/analysis/analytics_dashboard.html"
)
_emails = itertools.count()


def make_user(user_type, email=None, name="Test User"):
    return User.objects.create_user(
        email=email or f"response-pages-{next(_emails)}@example.com",
        password="strong-password",
        name=name,
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def make_survey(provider, title="Pages"):
    """Published survey: one choice, one rating and one open-text question."""
    survey = Survey.objects.create(provider=provider, title=title, status=SurveyStatus.PUBLISHED)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="Option A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="Option B", order_index=1)
    Question.objects.create(
        survey=survey,
        question_text="Rate the service",
        question_type=QuestionType.RATING_SCALE,
        order_index=1,
    )
    Question.objects.create(
        survey=survey,
        question_text="Any comments?",
        question_type=QuestionType.OPEN_TEXT,
        order_index=2,
        is_required=False,
    )
    return survey


@pytest.fixture
def provider():
    return make_user(UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    # Responses of another survey first, so that response ids differ from numbers.
    other = make_survey(make_user(UserType.SERVICE_PROVIDER), title="Other")
    for minutes in range(5):
        add_response(other, minutes=minutes)
    return make_survey(provider)


def add_response(
    survey,
    minutes=0,
    evidence=True,
    excluded=False,
    attention_failed=0,
    signals_ok=True,
    timings=True,
    active_ms=192_000,
    text="Great service",
    sentiment=(AnalysisStatus.COMPLETED, SentimentLabel.POSITIVE),
    respondent=None,
    device_hash="",
):
    """Store one response that answered every question; numbered by its minutes."""
    response = Response.objects.create(
        survey=survey,
        respondent=respondent or make_user(UserType.RESPONDENT),
        is_excluded=excluded,
        snap_gender="FEMALE",
    )
    Response.objects.filter(pk=response.pk).update(
        submitted_at=SUBMITTED + timedelta(minutes=minutes)
    )
    choice, rating, open_text = survey.questions.all()
    Answer.objects.create(response=response, question=choice, selected_option=choice.options.first())
    Answer.objects.create(response=response, question=rating, rating_value=3)
    if text is not None:
        answer = Answer.objects.create(response=response, question=open_text, answer_value=text)
        if sentiment is not None:
            SentimentAnalysisResult.objects.create(
                answer=answer, status=sentiment[0], sentiment_label=sentiment[1]
            )
    if evidence:
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=(
                [
                    {"question_id": question.question_id, "active_ms": 64_000}
                    for question in (choice, rating, open_text)
                ]
                if timings
                else []
            ),
            active_ms=active_ms,
            attention_total=1 if attention_failed else 0,
            attention_failed=attention_failed,
            rating_count=1,
            device_hash=device_hash,
            signals_ok=signals_ok,
        )
    return response


def add_responses(survey, count, **kwargs):
    return [add_response(survey, minutes=minutes, **kwargs) for minutes in range(count)]


def list_url(survey, **query):
    url = reverse("analysis:response_list", args=[survey.survey_id])
    if query:
        url += "?" + "&".join(f"{key}={value}" for key, value in query.items())
    return url


def detail_url(survey, number):
    return reverse("analysis:response_detail", args=[survey.survey_id, number])


def inclusion_url(survey, number):
    return reverse("analysis:response_inclusion", args=[survey.survey_id, number])


def get_page(client, provider, url):
    client.force_login(provider)
    response = client.get(url)
    assert response.status_code == 200
    return html.unescape(response.content.decode())


def text_of(content):
    """Return the page text with tags removed and spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", content))


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def exclusion_states(survey):
    return list(
        Response.objects.filter(survey=survey)
        .order_by("submitted_at", "response_id")
        .values_list("is_excluded", flat=True)
    )


# The list page.


def test_the_list_page_shows_the_approved_copy(client, provider, survey):
    add_response(survey, minutes=0)
    add_response(survey, minutes=1, attention_failed=2)  # 20 · Low
    add_response(survey, minutes=2, excluded=True, text=None)
    add_response(survey, minutes=3, evidence=False, sentiment=(AnalysisStatus.PENDING, None))
    add_response(survey, minutes=4, sentiment=(AnalysisStatus.FAILED, None))

    content = get_page(client, provider, list_url(survey))
    text = text_of(content)

    assert '<div class="page-kicker">Responses</div>' in content
    assert "<h1>Pages</h1>" in content
    assert SUBTITLE in content
    assert "Back to analytics" in content
    assert reverse("analysis:analytics_dashboard", args=[survey.survey_id]) in content
    assert '<label class="form-label" for="response-show">Show</label>' in content
    assert '<select class="form-select" id="response-show" name="show">' in content
    assert '<label class="form-label" for="response-order">Order</label>' in content
    assert '<select class="form-select" id="response-order" name="order">' in content
    for value, label in (
        ("all", "All responses"),
        ("included", "Included"),
        ("excluded", "Excluded"),
        ("flagged", "Flagged"),
        ("score", "Lowest score first"),
        ("newest", "Newest first"),
        ("oldest", "Oldest first"),
    ):
        assert re.search(rf'<option value="{value}"( selected)?>{label}</option>', content)
    assert '<option value="all" selected>All responses</option>' in content
    assert '<option value="score" selected>Lowest score first</option>' in content
    assert '<button type="submit" class="btn btn-outline-secondary">Apply</button>' in content
    assert "<strong>4 of 5</strong> responses included. 1 excluded.</p>" in content
    assert (
        '<th scope="col">Response</th><th scope="col">Submitted</th><th scope="col">Score</th>'
        '<th scope="col">Flags</th><th scope="col">Open answers</th><th scope="col">Status</th>'
        '<th scope="col"><span class="visually-hidden">Open</span></th>'
    ) in content

    rows = re.findall(r"<tr[^>]*>\s*<th scope=\"row\">.*?</tr>", content, re.S)
    cells = [text_of(row).strip() for row in rows]
    assert cells == [
        "Response 2 18 Nov 2026 20 · Low Failed attention check 1 positive Included Open",
        "Response 1 18 Nov 2026 100 · Clean No flag 1 positive Included Open",
        "Response 3 18 Nov 2026 100 · Clean No flag No open answer Excluded Open",
        "Response 5 18 Nov 2026 100 · Clean No flag Could not be analysed Included Open",
        "Response 4 18 Nov 2026 Before quality checks Not checked Waiting for analysis "
        "Included Open",
    ]
    assert "Showing 1 to 5 of 5 responses." in text
    assert "Previous" not in text
    assert "Next" not in text


def test_the_open_answers_cell_joins_the_counts(client, provider, survey):
    add_responses(survey, 4)
    response = add_response(survey, minutes=10)
    other_question = Question.objects.create(
        survey=survey,
        question_text="Anything else?",
        question_type=QuestionType.OPEN_TEXT,
        order_index=3,
        is_required=False,
    )
    answer = Answer.objects.create(response=response, question=other_question, answer_value="Fine")
    SentimentAnalysisResult.objects.create(
        answer=answer, status=AnalysisStatus.COMPLETED, sentiment_label=SentimentLabel.NEUTRAL
    )

    text = text_of(get_page(client, provider, list_url(survey, order="newest")))

    assert "Response 5 18 Nov 2026 100 · Clean No flag 1 positive, 1 neutral Included" in text


def test_rows_link_to_numbers_not_ids(client, provider, survey):
    responses = add_responses(survey, 5)
    # The other survey's five responses came first, so no id here is a number from 1 to 5.
    assert all(response.response_id > 5 for response in responses)

    content = get_page(client, provider, list_url(survey, order="oldest"))

    links = re.findall(r'href="([^"]*/responses/\d+/)"', content)
    assert links == [detail_url(survey, number) for number in range(1, 6)]
    for response in responses:
        assert detail_url(survey, response.response_id) not in content
    detail = get_page(client, provider, detail_url(survey, 3))
    assert re.findall(r'href="([^"]*/responses/\d+/)"', detail) == [
        detail_url(survey, 2),
        detail_url(survey, 4),
    ]
    assert inclusion_url(survey, 3) in detail
    for response in responses:
        assert f"/responses/{response.response_id}/" not in detail


def test_the_filters_and_orders_reach_the_page(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, minutes=9, attention_failed=1, excluded=True)

    content = get_page(client, provider, list_url(survey, show="flagged", order="newest"))

    assert '<option value="flagged" selected>Flagged</option>' in content
    assert '<option value="newest" selected>Newest first</option>' in content
    assert re.findall(r"Response (\d+)</th>", content) == ["5"]
    assert "Showing 1 to 1 of 1 responses." in text_of(content)
    assert "<strong>4 of 5</strong> responses included. 1 excluded.</p>" in content


def test_unknown_values_select_the_defaults(client, provider, survey):
    add_responses(survey, 5)

    content = get_page(client, provider, list_url(survey, show="nobody", order="random"))

    assert '<option value="all" selected>All responses</option>' in content
    assert '<option value="score" selected>Lowest score first</option>' in content


def test_thirty_responses_fill_two_pages(client, provider, survey):
    add_responses(survey, 30)

    first = get_page(client, provider, list_url(survey, order="oldest"))
    second = get_page(client, provider, list_url(survey, order="oldest", page=2))

    assert len(re.findall(r"Response \d+</th>", first)) == 25
    assert "Showing 1 to 25 of 30 responses." in text_of(first)
    assert 'href="' + list_url(survey, show="all", order="oldest", page=2) + '">Next</a>' in first
    assert ">Previous</a>" not in first

    assert re.findall(r"Response (\d+)</th>", second) == ["26", "27", "28", "29", "30"]
    assert "Showing 26 to 30 of 30 responses." in text_of(second)
    assert (
        'href="' + list_url(survey, show="all", order="oldest", page=1) + '">Previous</a>'
    ) in second
    assert ">Next</a>" not in second


def test_no_match_offers_all_responses(client, provider, survey):
    add_responses(survey, 5)

    content = get_page(client, provider, list_url(survey, show="excluded"))

    assert "No responses match this filter." in content
    assert f'<a href="{list_url(survey)}">Show all responses</a>' in content
    assert "<table" not in content


# The response page.


def test_the_response_page_shows_the_approved_copy(client, provider, survey):
    add_responses(survey, 3)
    add_response(survey, minutes=10, attention_failed=1)
    add_response(survey, minutes=11)

    content = get_page(client, provider, detail_url(survey, 4))
    text = text_of(content)

    assert '<div class="page-kicker">Pages · Response 4 of 5</div>' in content
    assert "<h1>Response 4</h1>" in content
    assert "Submitted 18 Nov 2026 · Active time 3 min 12 s</p>" in content
    assert "Back to responses" in content
    assert f'href="{list_url(survey)}"' in content
    assert '<h2 class="section-title">Answers</h2>' in content
    assert "1. Pick one Option A 2. Rate the service 3 of 5 3. Any comments? Great service Positive" in text
    assert '<h2 class="section-title">Response quality</h2>' in content
    assert "Score 60" in text
    assert "Check" in text
    assert f"{NAMES['ATTENTION_FAILED']} {MEANINGS['ATTENTION_FAILED']}" in text
    assert "No flag." not in text
    assert '<p class="response-status">Included in the results.</p>' in content
    assert 'name="action" value="exclude"' in content
    assert "Exclude this response</button>" in content
    assert "csrfmiddlewaretoken" in content
    assert KEPT in content
    assert f'href="{detail_url(survey, 3)}"' in content
    assert "Previous response</a>" in content
    assert f'href="{detail_url(survey, 5)}"' in content
    assert "Next response" in content


def test_previous_and_next_appear_only_when_they_exist(client, provider, survey):
    add_responses(survey, 5)

    first = get_page(client, provider, detail_url(survey, 1))
    last = get_page(client, provider, detail_url(survey, 5))

    assert "Previous response" not in first
    assert "Next response" in first
    assert "Previous response" in last
    assert "Next response" not in last


def test_attention_questions_show_the_answer_and_the_expected_value(client, provider, survey):
    pick = Question.objects.create(
        survey=survey,
        question_text="Choose Option B to show you are reading",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=3,
        is_attention_check=True,
    )
    QuestionOption.objects.create(question=pick, option_text="Option A", order_index=0)
    option_b = QuestionOption.objects.create(question=pick, option_text="Option B", order_index=1)
    pick.expected_option = option_b
    pick.save()
    rate = Question.objects.create(
        survey=survey,
        question_text="Choose 5 to show you are reading",
        question_type=QuestionType.RATING_SCALE,
        order_index=4,
        is_attention_check=True,
        is_required=False,
        expected_rating=5,
    )
    responses = []
    for minutes in range(5):
        response = Response.objects.create(survey=survey, respondent=make_user(UserType.RESPONDENT))
        Response.objects.filter(pk=response.pk).update(
            submitted_at=SUBMITTED + timedelta(minutes=minutes)
        )
        responses.append(response)
    Answer.objects.create(response=responses[0], question=pick, selected_option=option_b)
    Answer.objects.create(response=responses[0], question=rate, rating_value=2)

    content = get_page(client, provider, detail_url(survey, 1))

    assert content.count('<span class="badge text-bg-light">Attention check</span>') == 2
    assert '<p class="response-attention">Answered: <strong>Option B</strong> · Expected: Option B</p>' in content
    assert '<p class="response-attention">Answered: <strong>2 of 5</strong> · Expected: 5 of 5</p>' in content
    assert text_of(content).count("Not answered") == 3  # the three plain questions
    assert BEFORE_CHECKS in content

    second = get_page(client, provider, detail_url(survey, 2))
    assert '<p class="response-attention">Not answered · Expected: Option B</p>' in second
    assert '<p class="response-attention">Not answered · Expected: 5 of 5</p>' in second


def test_the_sentiment_label_under_an_open_answer(client, provider, survey):
    add_response(survey, minutes=0, sentiment=(AnalysisStatus.PENDING, None))
    add_response(survey, minutes=1, sentiment=(AnalysisStatus.FAILED, None))
    add_response(survey, minutes=2, sentiment=(AnalysisStatus.SKIPPED, None))
    add_response(survey, minutes=3, sentiment=None)
    add_response(survey, minutes=4, sentiment=(AnalysisStatus.COMPLETED, SentimentLabel.NEGATIVE))

    def label(number):
        content = get_page(client, provider, detail_url(survey, number))
        match = re.search(r'<p class="response-answer__sentiment">(.*?)</p>', content)
        return match.group(1) if match else None

    assert [label(number) for number in range(1, 6)] == [
        "Waiting for analysis",
        "Could not be analysed",
        None,
        None,
        "Negative",
    ]


@pytest.mark.parametrize(
    "active_ms, shown",
    [(192_000, "3 min 12 s"), (60_000, "1 min 0 s"), (59_999, "59 s"), (1_500, "1 s")],
)
def test_the_active_time(client, provider, survey, active_ms, shown):
    add_responses(survey, 5, active_ms=active_ms)

    content = get_page(client, provider, detail_url(survey, 1))

    assert f"Submitted 18 Nov 2026 · Active time {shown}</p>" in content


def test_no_active_time_without_evidence_or_active_time(client, provider, survey):
    add_response(survey, minutes=0, evidence=False)
    add_response(survey, minutes=1, active_ms=None, timings=False, signals_ok=False)
    for minutes in (5, 6, 7):
        add_response(survey, minutes=minutes)

    for number in (1, 2):
        content = get_page(client, provider, detail_url(survey, number))
        assert "Submitted 18 Nov 2026</p>" in content
        assert "Active time" not in content


def test_the_not_checked_lines(client, provider, survey):
    add_responses(survey, 5, timings=False)

    text = text_of(get_page(client, provider, detail_url(survey, 1)))

    assert "Score 100" in text
    assert "No flag." in text
    assert "Not checked: Failed attention check. This survey has no attention check." in text
    assert "Not checked: Answered very fast. Needs at least 3 answered closed questions." in text
    assert "Not checked: Same rating on every rating question. Needs 5 or more rating questions." in text
    assert "Same device as another account" not in text


def test_no_speed_line_when_the_timings_are_missing(client, provider, survey):
    add_responses(survey, 5, timings=False, signals_ok=False)

    text = text_of(get_page(client, provider, detail_url(survey, 1)))

    assert f"{NAMES['SIGNALS_MISSING']} {MEANINGS['SIGNALS_MISSING']}" in text
    assert "Not checked: Answered very fast" not in text
    assert "Not checked: Failed attention check. This survey has no attention check." in text


def test_before_quality_checks_shows_the_sentence_and_no_button(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, minutes=10, evidence=False)

    content = get_page(client, provider, detail_url(survey, 5))

    assert BEFORE_CHECKS in content
    assert 'class="response-score"' not in content
    assert '<p class="response-status">Included in the results.</p>' in content
    assert "Exclude this response" not in content
    assert "Include this response" not in content
    assert inclusion_url(survey, 5) not in content


def test_an_excluded_response_before_quality_checks_can_be_included(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, minutes=10, evidence=False, excluded=True)

    content = get_page(client, provider, detail_url(survey, 5))

    assert '<p class="response-status">Excluded from the results.</p>' in content
    assert "Include this response</button>" in content


def test_an_unknown_number_returns_to_the_list(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    response = client.get(detail_url(survey, 6))

    assert response.status_code == 302
    assert response.url == list_url(survey)
    assert messages_of(response) == ["Response does not belong to this survey."]


# Privacy.


def test_no_page_shows_who_answered_when_in_the_day_or_from_which_device(
    client, provider, survey
):
    respondent = make_user(UserType.RESPONDENT, email=SECRET_EMAIL, name=SECRET_NAME)
    add_response(survey, minutes=0, respondent=respondent, device_hash=DEVICE_HASH)
    add_responses(survey, 4)

    for url in (list_url(survey), detail_url(survey, 1)):
        content = get_page(client, provider, url)
        assert "18 Nov 2026" in content
        assert SECRET_EMAIL not in content
        assert "rania.secret" not in content
        assert SECRET_NAME not in content
        assert "FEMALE" not in content
        assert "Female" not in content
        assert DEVICE_HASH not in content
        assert "14:37" not in content
        assert "2:37" not in content


# Include or exclude one response.


def test_exclude_then_include_with_both_messages(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    excluded = client.post(inclusion_url(survey, 2), {"action": "exclude"})

    assert excluded.status_code == 302
    assert excluded.url == detail_url(survey, 2)
    assert messages_of(excluded) == [
        "Response 2 is excluded. You can include it again at any time."
    ]
    assert exclusion_states(survey) == [False, True, False, False, False]
    content = html.unescape(client.get(detail_url(survey, 2)).content.decode())
    assert '<p class="response-status">Excluded from the results.</p>' in content
    assert "Include this response</button>" in content

    again = client.post(inclusion_url(survey, 2), {"action": "exclude"})
    assert again.url == detail_url(survey, 2)
    assert messages_of(again) == []

    included = client.post(inclusion_url(survey, 2), {"action": "include"})

    assert included.url == detail_url(survey, 2)
    assert messages_of(included) == ["Response 2 is included again."]
    assert exclusion_states(survey) == [False] * 5


def test_a_get_to_the_inclusion_address_is_405(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    assert client.get(inclusion_url(survey, 1)).status_code == 405


def test_an_unknown_action_is_400(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    assert client.post(inclusion_url(survey, 1), {"action": "delete"}).status_code == 400
    assert client.post(inclusion_url(survey, 1)).status_code == 400
    assert exclusion_states(survey) == [False] * 5


def test_excluding_before_quality_checks_is_refused_on_the_page(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, minutes=10, evidence=False)
    client.force_login(provider)

    response = client.post(inclusion_url(survey, 5), {"action": "exclude"})

    assert response.url == detail_url(survey, 5)
    assert messages_of(response) == [BEFORE_CHECKS]
    assert exclusion_states(survey) == [False] * 5


def test_an_unknown_number_post_returns_to_the_list(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    response = client.post(inclusion_url(survey, 9), {"action": "exclude"})

    assert response.url == list_url(survey)
    assert messages_of(response) == ["Response does not belong to this survey."]


# Locked results, sign-in and ownership.


def test_both_pages_are_locked_under_five_responses(client, provider, survey):
    add_responses(survey, 4)

    for url in (list_url(survey), detail_url(survey, 1)):
        content = get_page(client, provider, url)
        assert LOCKED_HEADING in content
        assert (
            "This survey has 4 responses. Results stay hidden until at least 5 people "
            "have answered, so no answer can be traced back to one person."
        ) in content
        assert "Response 1</" not in content
        assert "Option A" not in content
        assert "Great service" not in content
        assert "18 Nov 2026" not in content


def test_a_locked_post_changes_nothing(client, provider, survey):
    add_responses(survey, 4)
    client.force_login(provider)

    response = client.post(inclusion_url(survey, 1), {"action": "exclude"})

    assert response.url == detail_url(survey, 1)
    assert messages_of(response) == ["Results open at 5 responses."]
    assert exclusion_states(survey) == [False] * 4


def test_not_logged_in_goes_to_the_login(client, survey):
    add_responses(survey, 5)

    for response in (
        client.get(list_url(survey)),
        client.get(detail_url(survey, 1)),
        client.post(inclusion_url(survey, 1), {"action": "exclude"}),
    ):
        assert response.status_code == 302
        assert response.url == reverse("users:login")
    assert exclusion_states(survey) == [False] * 5


def test_another_provider_is_sent_to_the_provider_dashboard(client, survey):
    add_responses(survey, 5)
    client.force_login(make_user(UserType.SERVICE_PROVIDER))

    for response in (
        client.get(list_url(survey)),
        client.get(detail_url(survey, 1)),
        client.post(inclusion_url(survey, 1), {"action": "exclude"}),
    ):
        assert response.status_code == 302
        assert response.url == reverse("surveys:provider_dashboard")
        assert messages_of(response)
    assert exclusion_states(survey) == [False] * 5


# The analytics page.


def test_view_responses_shows_only_while_the_results_are_open(client, provider, survey):
    add_responses(survey, 4)
    analytics = reverse("analysis:analytics_dashboard", args=[survey.survey_id])

    locked = get_page(client, provider, analytics)
    assert LOCKED_HEADING in locked
    assert "View responses" not in locked
    assert list_url(survey) not in locked

    add_response(survey, minutes=10)
    opened = get_page(client, provider, analytics)
    assert "View responses</a>" in opened
    assert f'href="{list_url(survey)}"' in opened
    assert opened.index("Back to surveys") < opened.index("View responses")


def test_the_copy_constants_match_the_quality_panel():
    template = TEMPLATE.read_text(encoding="utf-8")

    assert response_views.FLAG_NAMES == NAMES
    assert response_views.FLAG_MEANINGS == MEANINGS
    for code in QUALITY_FLAG_ORDER:
        assert response_views.FLAG_NAMES[code] in template
        assert response_views.FLAG_MEANINGS[code] in template
