"""W-05a: the sentiment panel of the analytics page and its retry action (TASK-36).

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import re
from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Answer, Question, Response, SentimentAnalysisResult, Survey, User
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository

TITLE = "Sentiment of open answers"
NO_OPEN_QUESTION = "This survey has no open-text question, so there is no sentiment to show."
NO_OPEN_ANSWERS = "No open answers to analyse yet."
HINT_TITLE = "Analysis is waiting."
HINT_BODY = (
    "The analysis worker may not be running. The answers are saved and counted; "
    "each one gets a label when the worker runs."
)
NO_CHART_YET = "The chart appears when the first answer is analysed."
FAILED_BODY = "The answers are saved and counted in the results."
CANVAS = 'id="sentimentDistributionChart"'

POSITIVE = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.POSITIVE})
NEUTRAL = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.NEUTRAL})
NEGATIVE = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.NEGATIVE})
PENDING = (AnalysisStatus.PENDING, {})
SKIPPED = (AnalysisStatus.SKIPPED, {"error_code": "no_text"})


def failed(code):
    return (AnalysisStatus.FAILED, {"error_code": code})


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey(
    results=(), question_type=QuestionType.OPEN_TEXT, submitted_ago=None, responses=5
):
    """Create a survey with one question, at least `responses` responses, one result per entry.

    Each entry of `results` is (status, fields) for the answer of one response; the
    responses beyond the entries have an answer and no result.
    """
    provider = create_user("provider-panel@example.com", UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Any comments?",
            question_type=question_type,
            is_required=True,
            order_index=0,
        )
    )
    results = list(results)
    for index in range(max(responses, len(results))):
        respondent = create_user(f"respondent-panel-{index}@example.com", UserType.RESPONDENT)
        response = ResponseRepository().save(Response(survey=survey, respondent=respondent))
        if question_type == QuestionType.RATING_SCALE:
            ResponseRepository().save_answer(
                Answer(response=response, question=question, rating_value=4)
            )
            continue
        answer = ResponseRepository().save_answer(
            Answer(response=response, question=question, answer_value=f"Answer {index}")
        )
        if index < len(results):
            status, fields = results[index]
            SentimentAnalysisResult.objects.create(answer=answer, status=status, **fields)
    if submitted_ago is not None:
        Response.objects.filter(survey=survey).update(
            submitted_at=timezone.now() - submitted_ago
        )
    return provider, survey


def get_dashboard(client, provider, survey):
    client.force_login(provider)
    url = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    return client.get(url).content.decode()


def post_retry(client, user, survey):
    client.force_login(user)
    return client.post(reverse("analysis:retry_failed", args=[survey.survey_id]))


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def in_order(content, *parts):
    positions = [content.index(part) for part in parts]
    return positions == sorted(positions)


# State 1: all analysed


@pytest.mark.django_db
def test_all_analysed_shows_count_line_chart_centre_legend_and_skipped_caption(client):
    provider, survey = create_survey([POSITIVE, POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, SKIPPED])

    content = get_dashboard(client, provider, survey)

    assert TITLE in content
    assert "Analysed 5 of 5 open answers.</p>" in content
    assert CANVAS in content
    assert re.search(r'sentiment-chart-centre[^>]*>\s*<strong>5</strong>', content)
    assert re.search(r"Positive <strong>3</strong> <span>60%</span>", content)
    assert re.search(r"Neutral <strong>1</strong> <span>20%</span>", content)
    assert re.search(r"Negative <strong>1</strong> <span>20%</span>", content)
    assert "1 answer had no words to analyse and is left out." in content
    assert HINT_TITLE not in content
    assert "Retry failed answers" not in content
    assert in_order(content, "Analysed 5 of 5", CANVAS, "had no words to analyse")


@pytest.mark.django_db
def test_skipped_caption_uses_the_plural(client):
    provider, survey = create_survey([POSITIVE] * 4 + [SKIPPED, SKIPPED])

    content = get_dashboard(client, provider, survey)

    assert "2 answers had no words to analyse and are left out." in content


@pytest.mark.django_db
def test_metric_captions_read_rate_of_analysed(client):
    provider, survey = create_survey([POSITIVE, POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, PENDING])

    content = get_dashboard(client, provider, survey)

    assert "<small>60% of 5 analysed</small>" in content
    assert "<small>20% of 5 analysed</small>" in content
    # W-05b (TASK-48) replaced the "Analytics summary" card with the group breakdown card.
    assert "Group breakdown" in content


# State 2: waiting, worker running


@pytest.mark.django_db
def test_waiting_shows_count_line_chart_and_plural_caption(client):
    provider, survey = create_survey([POSITIVE, POSITIVE, NEGATIVE, PENDING, PENDING])

    content = get_dashboard(client, provider, survey)

    assert "Analysed 3 of 5 open answers. 2 waiting.</p>" in content
    assert CANVAS in content
    assert (
        "2 answers are waiting for the analysis worker. Reload the page to update." in content
    )
    assert HINT_TITLE not in content
    assert in_order(content, "Analysed 3 of 5", CANVAS, "are waiting for the analysis worker")


@pytest.mark.django_db
def test_one_waiting_answer_uses_the_singular(client):
    provider, survey = create_survey([POSITIVE, POSITIVE, POSITIVE, POSITIVE, PENDING])

    content = get_dashboard(client, provider, survey)

    assert "1 answer is waiting for the analysis worker. Reload the page to update." in content


# State 3: worker hint


@pytest.mark.django_db
def test_overdue_analysis_shows_the_worker_hint_and_no_chart(client):
    provider, survey = create_survey([PENDING] * 5, submitted_ago=timedelta(minutes=10))

    content = get_dashboard(client, provider, survey)

    assert "Analysed 0 of 5 open answers. 5 waiting.</p>" in content
    assert HINT_TITLE in content
    assert HINT_BODY in content
    assert NO_CHART_YET in content
    assert CANVAS not in content
    assert in_order(content, "Analysed 0 of 5", HINT_TITLE, NO_CHART_YET, "5 answers are waiting")


# State 4: failed, with retry


@pytest.mark.django_db
def test_failed_shows_reasons_and_the_retry_form(client):
    provider, survey = create_survey(
        [POSITIVE, POSITIVE, NEUTRAL, failed("payment_required"), failed("payment_required"),
         failed("")]
    )

    content = get_dashboard(client, provider, survey)

    assert "Analysed 3 of 6 open answers. 3 failed.</p>" in content
    assert "3 answers could not be analysed." in content
    assert "The analysis service needs payment. (2)" in content
    assert "The reason was not recorded. (1)" in content
    assert FAILED_BODY in content
    action = reverse("analysis:retry_failed", args=[survey.survey_id])
    assert re.search(rf'<form method="post" action="{action}"', content)
    assert "csrfmiddlewaretoken" in content
    assert "Retry failed answers" in content
    assert in_order(content, "Analysed 3 of 6", "could not be analysed", CANVAS)


@pytest.mark.django_db
def test_one_failed_answer_uses_the_singular_and_the_other_reasons_have_their_lines(client):
    provider, survey = create_survey([POSITIVE] * 4 + [failed("unavailable")])

    content = get_dashboard(client, provider, survey)

    assert "Analysed 4 of 5 open answers. 1 failed.</p>" in content
    assert "1 answer could not be analysed." in content
    assert "The analysis service could not be reached after 3 tries. (1)" in content


@pytest.mark.django_db
def test_count_line_shows_waiting_and_failed_together(client):
    provider, survey = create_survey([POSITIVE, POSITIVE, PENDING, failed("config"),
                                      failed("bad_output")])

    content = get_dashboard(client, provider, survey)

    assert "Analysed 2 of 5 open answers. 1 waiting. 2 failed.</p>" in content
    assert "The analysis service is not set up. (1)" in content
    assert "The analysis service returned an unknown result. (1)" in content


# States 5 and 6: empty states


@pytest.mark.django_db
def test_survey_without_an_open_text_question_shows_its_empty_state(client):
    provider, survey = create_survey(question_type=QuestionType.RATING_SCALE)

    content = get_dashboard(client, provider, survey)

    assert NO_OPEN_QUESTION in content
    assert "Analysed" not in content
    assert CANVAS not in content


@pytest.mark.django_db
def test_open_question_without_analysed_rows_shows_no_open_answers(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey)

    assert NO_OPEN_ANSWERS in content
    assert NO_OPEN_QUESTION not in content
    assert "Analysed" not in content
    assert CANVAS not in content


# Page rules


@pytest.mark.django_db
def test_page_has_no_chart_js_badge_and_no_hex_colour(client):
    provider, survey = create_survey([POSITIVE] * 5)

    content = get_dashboard(client, provider, survey)

    assert "bi-pie-chart" not in content
    assert "</i>Chart.js" not in content
    assert "Sentiment distribution" not in content
    hex_values = [
        value
        for value in re.findall(r"(?<!&)#[0-9A-Fa-f]{3,8}\b", content)
        if value != f"#{survey.survey_id}"
    ]
    assert hex_values == []


# Retry action


@pytest.mark.django_db
def test_retry_resets_the_failed_rows_and_shows_the_plural_message(client):
    provider, survey = create_survey([POSITIVE] * 3 + [failed("payment_required")] * 2)

    response = post_retry(client, provider, survey)

    assert response.status_code == 302
    assert response.url == reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    assert messages_of(response) == ["2 answers are queued for analysis again."]
    assert not SentimentAnalysisResult.objects.filter(status=AnalysisStatus.FAILED).exists()
    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.PENDING).count() == 2


@pytest.mark.django_db
def test_retry_of_one_row_shows_the_singular_message(client):
    provider, survey = create_survey([POSITIVE] * 4 + [failed("config")])

    response = post_retry(client, provider, survey)

    assert messages_of(response) == ["1 answer is queued for analysis again."]


@pytest.mark.django_db
def test_retry_by_another_provider_is_refused(client):
    _, survey = create_survey([POSITIVE] * 4 + [failed("config")])
    other = create_user("other-panel@example.com", UserType.SERVICE_PROVIDER)

    response = post_retry(client, other, survey)

    assert response.status_code == 302
    assert messages_of(response) == ["Only the survey owner can view survey analytics."]
    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.FAILED).count() == 1


@pytest.mark.django_db
def test_retry_while_results_are_locked_is_refused(client):
    provider, survey = create_survey([failed("config")], responses=4)

    response = post_retry(client, provider, survey)

    assert messages_of(response) == ["Results open at 5 responses."]
    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.FAILED).count() == 1


@pytest.mark.django_db
def test_retry_refuses_get(client):
    provider, survey = create_survey([failed("config")])
    client.force_login(provider)

    response = client.get(reverse("analysis:retry_failed", args=[survey.survey_id]))

    assert response.status_code == 405
