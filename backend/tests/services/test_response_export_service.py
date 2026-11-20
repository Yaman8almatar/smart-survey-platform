"""TASK-51 (FR-14): ResponseReviewService.export_responses gives the included responses as rows.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import itertools
from datetime import datetime, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

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
from core.exceptions import UnauthorizedAction
from services.quality_rules import ATTENTION_FAILED, BEFORE_CHECKS, CLEAN, EVALUATED, LOW
from services.quality_service import QualityService
from services.response_review_service import ResponseReviewService

pytestmark = pytest.mark.django_db

ROW_KEYS = {"number", "submitted_at", "status", "score", "band", "flags", "answers"}
QUESTION_KEYS = {"position", "question_text", "question_type"}
BASE = timezone.make_aware(datetime(2026, 11, 18, 14, 37))
SECRET_EMAIL = "export-secret@example.com"
DEVICE_HASH = "f0e1d2c3" * 8
_emails = itertools.count()


def make_user(user_type, email=None):
    return User.objects.create_user(
        email=email or f"export-service-{next(_emails)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def make_survey(provider):
    """Published survey: one choice, one rating and one open-text question."""
    survey = Survey.objects.create(provider=provider, title="Export", status=SurveyStatus.PUBLISHED)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="B", order_index=1)
    Question.objects.create(
        survey=survey,
        question_text="Rate it",
        question_type=QuestionType.RATING_SCALE,
        order_index=1,
        is_required=False,
    )
    Question.objects.create(
        survey=survey,
        question_text="Comment",
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
    return make_survey(provider)


def add_response(
    survey,
    minutes,
    evidence=True,
    attention_failed=0,
    excluded=False,
    rating=4,
    text="Text",
    sentiment=(AnalysisStatus.COMPLETED, SentimentLabel.POSITIVE),
    respondent=None,
    device_hash="",
):
    """Store one response that picked A, rated `rating` and wrote `text`; numbered by minutes."""
    response = Response.objects.create(
        survey=survey,
        respondent=respondent or make_user(UserType.RESPONDENT),
        is_excluded=excluded,
        snap_gender="FEMALE",
    )
    Response.objects.filter(pk=response.pk).update(submitted_at=BASE + timedelta(minutes=minutes))
    choice, rate, comment = survey.questions.all()
    Answer.objects.create(response=response, question=choice, selected_option=choice.options.first())
    if rating is not None:
        Answer.objects.create(response=response, question=rate, rating_value=rating)
    if text is not None:
        answer = Answer.objects.create(response=response, question=comment, answer_value=text)
        if sentiment is not None:
            SentimentAnalysisResult.objects.create(
                answer=answer, status=sentiment[0], sentiment_label=sentiment[1]
            )
    if evidence:
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=[],
            active_ms=192_000,
            attention_total=1 if attention_failed else 0,
            attention_failed=attention_failed,
            device_hash=device_hash,
            signals_ok=True,
        )
    return response


def export(provider, survey):
    return ResponseReviewService().export_responses(provider, survey.survey_id)


def numbers(result):
    return [row["number"] for row in result["rows"]]


def test_rows_are_the_included_responses_under_the_list_numbers(provider, survey):
    for minutes in (50, 10, 40, 0, 30, 20):
        add_response(survey, minutes=minutes)
    QualityService().set_response_inclusion(provider, survey.survey_id, 2, True)

    result = export(provider, survey)
    listing = ResponseReviewService().list_responses(provider, survey.survey_id, order="oldest")

    assert numbers(result) == [1, 3, 4, 5, 6]
    assert [row["submitted_at"] for row in result["rows"]] == [
        BASE + timedelta(minutes=minutes) for minutes in (0, 20, 30, 40, 50)
    ]
    included = {row["number"]: row["submitted_at"] for row in listing["rows"] if not row["is_excluded"]}
    assert {row["number"]: row["submitted_at"] for row in result["rows"]} == included


def test_the_result_holds_exactly_the_approved_keys(provider, survey):
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    result = export(provider, survey)

    assert set(result) == {"locked", "questions", "rows"}
    assert result["locked"] is False
    assert result["questions"] == [
        {"position": 1, "question_text": "Pick one", "question_type": QuestionType.MULTIPLE_CHOICE},
        {"position": 2, "question_text": "Rate it", "question_type": QuestionType.RATING_SCALE},
        {"position": 3, "question_text": "Comment", "question_type": QuestionType.OPEN_TEXT},
    ]
    for question in result["questions"]:
        assert set(question) == QUESTION_KEYS
    for row in result["rows"]:
        assert set(row) == ROW_KEYS
        assert len(row["answers"]) == 3
        for answer in row["answers"]:
            assert set(answer) == {"value", "sentiment"}


def test_answer_values_and_every_sentiment_state(provider, survey):
    completed = AnalysisStatus.COMPLETED
    sentiments = [
        (completed, SentimentLabel.POSITIVE),
        (completed, SentimentLabel.NEUTRAL),
        (completed, SentimentLabel.NEGATIVE),
        (AnalysisStatus.PENDING, None),
        (AnalysisStatus.RUNNING, None),
        (AnalysisStatus.FAILED, None),
        (AnalysisStatus.SKIPPED, None),
        None,  # an open answer without a result
    ]
    for minutes, sentiment in enumerate(sentiments):
        add_response(survey, minutes=minutes, sentiment=sentiment)
    add_response(survey, minutes=20, rating=None, text=None)  # two questions left unanswered

    rows = export(provider, survey)["rows"]

    assert [row["answers"][2]["sentiment"] for row in rows] == [
        "positive",
        "neutral",
        "negative",
        "waiting",
        "waiting",
        "failed",
        None,
        None,
        None,
    ]
    assert rows[0]["answers"] == [
        {"value": "A", "sentiment": None},
        {"value": 4, "sentiment": None},
        {"value": "Text", "sentiment": "positive"},
    ]
    assert rows[-1]["answers"] == [
        {"value": "A", "sentiment": None},
        {"value": None, "sentiment": None},
        {"value": None, "sentiment": None},
    ]


def test_the_quality_verdicts_and_a_response_before_checks(provider, survey):
    add_response(survey, minutes=0)
    add_response(survey, minutes=1, attention_failed=2)
    add_response(survey, minutes=2, evidence=False)
    add_response(survey, minutes=3)
    add_response(survey, minutes=4)

    rows = {row["number"]: row for row in export(provider, survey)["rows"]}

    assert (rows[1]["status"], rows[1]["score"], rows[1]["band"], rows[1]["flags"]) == (
        EVALUATED, 100, CLEAN, []
    )
    assert (rows[2]["score"], rows[2]["band"], rows[2]["flags"]) == (20, LOW, [ATTENTION_FAILED])
    assert (rows[3]["status"], rows[3]["score"], rows[3]["band"], rows[3]["flags"]) == (
        BEFORE_CHECKS, None, None, []
    )
    assert rows[3]["answers"][0] == {"value": "A", "sentiment": None}


def test_locked_results_return_the_locked_result_only(provider, survey):
    for minutes in range(4):
        add_response(survey, minutes=minutes)

    with CaptureQueriesContext(connection) as queries:
        result = export(provider, survey)

    assert result == {
        "survey_id": survey.survey_id,
        "locked": True,
        "response_count": 4,
        "min_responses": 5,
    }
    assert len(queries.captured_queries) == 2  # the owner check and the count


def test_another_provider_is_refused(survey):
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    with pytest.raises(UnauthorizedAction):
        export(make_user(UserType.SERVICE_PROVIDER), survey)


def query_count(count):
    """Return the query count of an export of a new survey with `count` responses."""
    provider = make_user(UserType.SERVICE_PROVIDER)
    survey = make_survey(provider)
    for minutes in range(count):
        add_response(survey, minutes=minutes)
    with CaptureQueriesContext(connection) as queries:
        export(provider, survey)
    return len(queries.captured_queries)


def test_query_counts_do_not_grow_with_the_responses():
    assert query_count(5) == query_count(12)


def walk(value, keys, leaves):
    """Collect every dictionary key and every leaf value of a nested result."""
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            walk(item, keys, leaves)
    elif isinstance(value, (list, tuple)):
        for item in value:
            walk(item, keys, leaves)
    else:
        leaves.append(value)


def test_no_result_holds_an_id_an_email_or_a_device_value(provider, survey):
    respondent = make_user(UserType.RESPONDENT, email=SECRET_EMAIL)
    add_response(survey, minutes=0, respondent=respondent, device_hash=DEVICE_HASH)
    for minutes in range(1, 5):
        add_response(survey, minutes=minutes)

    keys, leaves = set(), []
    walk(export(provider, survey), keys, leaves)

    assert not keys & {
        "response_id",
        "respondent_id",
        "respondent",
        "survey_id",
        "device_hash",
        "timings",
        "active_ms",
        "snap_gender",
        "email",
    }
    texts = [leaf for leaf in leaves if isinstance(leaf, str)]
    assert not any(SECRET_EMAIL in text or DEVICE_HASH in text or "FEMALE" in text for text in texts)
    # The only integers are numbers, positions, the rating and the score: no id slips in.
    ints = {leaf for leaf in leaves if type(leaf) is int}
    assert ints == {1, 2, 3, 4, 5, 100}
