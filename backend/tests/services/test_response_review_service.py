"""TASK-49 (FR-07, FR-09, board W-07): ResponseReviewService lists and shows responses by number.

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
from core.exceptions import ResponseNotFound, UnauthorizedAction
from services.quality_rules import ATTENTION_FAILED, BEFORE_CHECKS, CHECK, CLEAN, EVALUATED, LOW
from services.quality_service import QualityService
from services.response_review_service import ResponseReviewService

pytestmark = pytest.mark.django_db

ROW_KEYS = {
    "number",
    "submitted_at",
    "status",
    "score",
    "band",
    "flags",
    "is_excluded",
    "open_answers",
}
DETAIL_KEYS = {
    "locked",
    "number",
    "total",
    "submitted_at",
    "active_ms",
    "is_excluded",
    "status",
    "score",
    "band",
    "flags",
    "not_checked",
    "previous_number",
    "next_number",
    "answers",
}
ANSWER_KEYS = {
    "position",
    "question_text",
    "question_type",
    "answered",
    "value",
    "is_attention_check",
    "expected",
    "sentiment",
}
NO_OPEN_ANSWERS = {"positive": 0, "neutral": 0, "negative": 0, "waiting": 0, "failed": 0}
BASE = timezone.make_aware(datetime(2026, 11, 18, 9, 0))
_emails = itertools.count()


def make_user(user_type):
    return User.objects.create_user(
        email=f"review-service-{next(_emails)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def make_survey(provider):
    """Published survey: one choice and two open-text questions."""
    survey = Survey.objects.create(provider=provider, title="Review", status=SurveyStatus.PUBLISHED)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="B", order_index=1)
    for index in (1, 2):
        Question.objects.create(
            survey=survey,
            question_text=f"Comment {index}",
            question_type=QuestionType.OPEN_TEXT,
            order_index=index,
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
    minutes=None,
    evidence=True,
    attention_failed=0,
    excluded=False,
    sentiments=(),
    active_ms=192_000,
):
    """Store one response that picked A and wrote one text per given sentiment result."""
    response = Response.objects.create(
        survey=survey, respondent=make_user(UserType.RESPONDENT), is_excluded=excluded
    )
    if minutes is not None:
        Response.objects.filter(pk=response.pk).update(
            submitted_at=BASE + timedelta(minutes=minutes)
        )
    questions = list(survey.questions.all())
    Answer.objects.create(
        response=response, question=questions[0], selected_option=questions[0].options.first()
    )
    for question, (status, label) in zip(questions[1:], sentiments):
        answer = Answer.objects.create(response=response, question=question, answer_value="Text")
        SentimentAnalysisResult.objects.create(answer=answer, status=status, sentiment_label=label)
    if evidence:
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=[],
            active_ms=active_ms,
            attention_total=1 if attention_failed else 0,
            attention_failed=attention_failed,
            signals_ok=True,
        )
    return response


def numbers(result):
    return [row["number"] for row in result["rows"]]


def test_numbers_follow_the_submit_time_then_the_id(provider, survey):
    first_created = add_response(survey, minutes=60)
    later_id_first = add_response(survey, minutes=0)  # a later id submitted earlier
    tie_low = add_response(survey, minutes=120)
    tie_high = add_response(survey, minutes=120)  # same time: the lower id comes first
    add_response(survey, minutes=180)
    assert tie_low.response_id < tie_high.response_id

    result = ResponseReviewService().list_responses(provider, survey.survey_id, order="oldest")

    assert numbers(result) == [1, 2, 3, 4, 5]
    assert [row["submitted_at"] for row in result["rows"]] == [
        BASE,
        BASE + timedelta(minutes=60),
        BASE + timedelta(minutes=120),
        BASE + timedelta(minutes=120),
        BASE + timedelta(minutes=180),
    ]

    QualityService().set_response_inclusion(provider, survey.survey_id, 1, True)
    later_id_first.refresh_from_db()
    first_created.refresh_from_db()
    assert later_id_first.is_excluded is True
    assert first_created.is_excluded is False

    QualityService().set_response_inclusion(provider, survey.survey_id, 4, True)
    tie_high.refresh_from_db()
    tie_low.refresh_from_db()
    assert (tie_low.is_excluded, tie_high.is_excluded) == (False, True)


def test_the_list_shows_the_number_set_response_inclusion_uses(provider, survey):
    for minutes in (40, 10, 30, 0, 20):
        add_response(survey, minutes=minutes)

    QualityService().set_response_inclusion(provider, survey.survey_id, 3, True)
    result = ResponseReviewService().list_responses(provider, survey.survey_id, order="oldest")

    assert [row["is_excluded"] for row in result["rows"]] == [False, False, True, False, False]
    detail = ResponseReviewService().get_response(provider, survey.survey_id, 3)
    assert detail["is_excluded"] is True
    assert detail["submitted_at"] == BASE + timedelta(minutes=20)


def test_rows_hold_exactly_the_approved_keys(provider, survey):
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    result = ResponseReviewService().list_responses(provider, survey.survey_id)

    assert set(result) == {"locked", "total", "included", "excluded", "show", "order", "rows"}
    assert result["locked"] is False
    for row in result["rows"]:
        assert set(row) == ROW_KEYS
        assert set(row["open_answers"]) == set(NO_OPEN_ANSWERS)


def test_order_by_score_puts_the_lowest_first_and_before_checks_last(provider, survey):
    add_response(survey, minutes=0)  # 1: 100
    add_response(survey, minutes=1, attention_failed=2)  # 2: 20
    add_response(survey, minutes=2, evidence=False)  # 3: before checks
    add_response(survey, minutes=3, attention_failed=1)  # 4: 60
    add_response(survey, minutes=4)  # 5: 100
    add_response(survey, minutes=5, evidence=False)  # 6: before checks

    result = ResponseReviewService().list_responses(provider, survey.survey_id)

    assert result["order"] == "score"
    assert numbers(result) == [2, 4, 1, 5, 3, 6]
    rows = {row["number"]: row for row in result["rows"]}
    assert (rows[2]["score"], rows[2]["band"], rows[2]["flags"]) == (20, LOW, [ATTENTION_FAILED])
    assert (rows[4]["score"], rows[4]["band"]) == (60, CHECK)
    assert (rows[1]["score"], rows[1]["band"], rows[1]["status"]) == (100, CLEAN, EVALUATED)
    assert (rows[3]["score"], rows[3]["band"], rows[3]["status"]) == (None, None, BEFORE_CHECKS)


def test_newest_and_oldest_orders(provider, survey):
    for minutes in range(6):
        add_response(survey, minutes=minutes)
    service = ResponseReviewService()

    assert numbers(service.list_responses(provider, survey.survey_id, order="newest")) == [
        6, 5, 4, 3, 2, 1,
    ]
    assert numbers(service.list_responses(provider, survey.survey_id, order="oldest")) == [
        1, 2, 3, 4, 5, 6,
    ]


def test_each_filter_keeps_the_totals_of_the_whole_survey(provider, survey):
    add_response(survey, minutes=0)  # 1
    add_response(survey, minutes=1, attention_failed=1)  # 2: flagged, included
    add_response(survey, minutes=2, attention_failed=1, excluded=True)  # 3: flagged, excluded
    add_response(survey, minutes=3, excluded=True)  # 4: excluded
    add_response(survey, minutes=4)  # 5
    service = ResponseReviewService()

    def shown(show):
        result = service.list_responses(provider, survey.survey_id, show=show, order="oldest")
        assert (result["total"], result["included"], result["excluded"]) == (5, 3, 2)
        assert result["show"] == show
        return numbers(result)

    assert shown("all") == [1, 2, 3, 4, 5]
    assert shown("included") == [1, 2, 5]
    assert shown("excluded") == [3, 4]
    assert shown("flagged") == [2, 3]


@pytest.mark.parametrize("show, order", [("everything", "random"), (None, None), ("", "")])
def test_unknown_values_fall_back_to_the_defaults(provider, survey, show, order):
    add_response(survey, minutes=0, attention_failed=1)
    for minutes in range(1, 5):
        add_response(survey, minutes=minutes, excluded=True)

    result = ResponseReviewService().list_responses(
        provider, survey.survey_id, show=show, order=order
    )

    assert (result["show"], result["order"]) == ("all", "score")
    assert numbers(result) == [1, 2, 3, 4, 5]


def test_open_answers_are_counted_per_response(provider, survey):
    completed = AnalysisStatus.COMPLETED
    add_response(
        survey,
        minutes=0,
        sentiments=[(completed, SentimentLabel.POSITIVE), (completed, SentimentLabel.NEUTRAL)],
    )
    add_response(
        survey, minutes=1, sentiments=[(AnalysisStatus.PENDING, None), (AnalysisStatus.RUNNING, None)]
    )
    add_response(
        survey, minutes=2, sentiments=[(AnalysisStatus.FAILED, None), (AnalysisStatus.SKIPPED, None)]
    )
    add_response(survey, minutes=3)
    add_response(
        survey,
        minutes=4,
        excluded=True,
        sentiments=[(completed, SentimentLabel.NEGATIVE), (completed, SentimentLabel.NEGATIVE)],
    )

    result = ResponseReviewService().list_responses(provider, survey.survey_id, order="oldest")

    assert [row["open_answers"] for row in result["rows"]] == [
        {**NO_OPEN_ANSWERS, "positive": 1, "neutral": 1},
        {**NO_OPEN_ANSWERS, "waiting": 2},
        {**NO_OPEN_ANSWERS, "failed": 1},
        NO_OPEN_ANSWERS,
        {**NO_OPEN_ANSWERS, "negative": 2},
    ]


def test_locked_results_return_the_locked_result_only(provider, survey):
    for minutes in range(4):
        add_response(survey, minutes=minutes)
    service = ResponseReviewService()
    locked = {
        "survey_id": survey.survey_id,
        "locked": True,
        "response_count": 4,
        "min_responses": 5,
    }

    with CaptureQueriesContext(connection) as listing:
        assert service.list_responses(provider, survey.survey_id) == locked
    assert service.get_response(provider, survey.survey_id, 1) == locked
    assert len(listing.captured_queries) == 2  # the owner check and the count


def test_another_provider_is_refused(survey):
    for minutes in range(5):
        add_response(survey, minutes=minutes)
    other = make_user(UserType.SERVICE_PROVIDER)
    service = ResponseReviewService()

    with pytest.raises(UnauthorizedAction):
        service.list_responses(other, survey.survey_id)
    with pytest.raises(UnauthorizedAction):
        service.get_response(other, survey.survey_id, 1)


def query_counts(count):
    """Return the query counts of both methods for a new survey with `count` responses."""
    provider = make_user(UserType.SERVICE_PROVIDER)
    survey = make_survey(provider)
    completed = AnalysisStatus.COMPLETED
    for minutes in range(count):
        add_response(
            survey,
            minutes=minutes,
            sentiments=[(completed, SentimentLabel.POSITIVE), (AnalysisStatus.PENDING, None)],
        )
    service = ResponseReviewService()
    with CaptureQueriesContext(connection) as listing:
        service.list_responses(provider, survey.survey_id)
    with CaptureQueriesContext(connection) as detail:
        service.get_response(provider, survey.survey_id, 3)
    return len(listing.captured_queries), len(detail.captured_queries)


def test_query_counts_do_not_grow_with_the_responses():
    assert query_counts(5) == query_counts(12)


def test_the_response_page_data(provider, survey):
    questions = list(survey.questions.all())
    pick = Question.objects.create(
        survey=survey,
        question_text="Choose B to show you are reading",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=3,
        is_attention_check=True,
    )
    QuestionOption.objects.create(question=pick, option_text="A", order_index=0)
    option_b = QuestionOption.objects.create(question=pick, option_text="B", order_index=1)
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
    for minutes in range(5):
        add_response(survey, minutes=minutes)
    third = add_response(
        survey,
        minutes=2.5,
        attention_failed=1,
        sentiments=[(AnalysisStatus.COMPLETED, SentimentLabel.NEGATIVE)],
    )
    Answer.objects.create(response=third, question=pick, selected_option=pick.options.first())

    detail = ResponseReviewService().get_response(provider, survey.survey_id, 4)

    assert set(detail) == DETAIL_KEYS
    assert (detail["number"], detail["total"]) == (4, 6)
    assert detail["submitted_at"] == BASE + timedelta(minutes=2.5)
    assert detail["active_ms"] == 192_000
    assert (detail["score"], detail["band"], detail["flags"]) == (60, CHECK, [ATTENTION_FAILED])
    assert (detail["previous_number"], detail["next_number"]) == (3, 5)
    assert detail["answers"] == [
        {
            "position": 1,
            "question_text": "Pick one",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "answered": True,
            "value": "A",
            "is_attention_check": False,
            "expected": None,
            "sentiment": None,
        },
        {
            "position": 2,
            "question_text": questions[1].question_text,
            "question_type": QuestionType.OPEN_TEXT,
            "answered": True,
            "value": "Text",
            "is_attention_check": False,
            "expected": None,
            "sentiment": "negative",
        },
        {
            "position": 3,
            "question_text": questions[2].question_text,
            "question_type": QuestionType.OPEN_TEXT,
            "answered": False,
            "value": None,
            "is_attention_check": False,
            "expected": None,
            "sentiment": None,
        },
        {
            "position": 4,
            "question_text": "Choose B to show you are reading",
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "answered": True,
            "value": "A",
            "is_attention_check": True,
            "expected": "B",
            "sentiment": None,
        },
        {
            "position": 5,
            "question_text": "Choose 5 to show you are reading",
            "question_type": QuestionType.RATING_SCALE,
            "answered": False,
            "value": None,
            "is_attention_check": True,
            "expected": 5,
            "sentiment": None,
        },
    ]
    for item in detail["answers"]:
        assert set(item) == ANSWER_KEYS


def test_an_attention_flag_without_an_expected_answer_is_a_plain_question(provider, survey):
    Question.objects.create(
        survey=survey,
        question_text="Marked but without an expected answer",
        question_type=QuestionType.RATING_SCALE,
        order_index=3,
        is_attention_check=True,
        is_required=False,
    )
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    detail = ResponseReviewService().get_response(provider, survey.survey_id, 1)

    assert detail["answers"][-1]["is_attention_check"] is False
    assert detail["answers"][-1]["expected"] is None


@pytest.mark.parametrize(
    "number, previous_number, next_number", [(1, None, 2), (5, 4, None)]
)
def test_previous_and_next_at_both_ends(provider, survey, number, previous_number, next_number):
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    detail = ResponseReviewService().get_response(provider, survey.survey_id, number)

    assert (detail["previous_number"], detail["next_number"]) == (previous_number, next_number)


@pytest.mark.parametrize("number", [0, 6, -1])
def test_an_unknown_number_is_refused(provider, survey, number):
    for minutes in range(5):
        add_response(survey, minutes=minutes)

    with pytest.raises(ResponseNotFound, match="Response does not belong to this survey."):
        ResponseReviewService().get_response(provider, survey.survey_id, number)


def test_no_result_holds_an_id_or_a_device_value(provider, survey):
    for minutes in range(5):
        add_response(survey, minutes=minutes)
    service = ResponseReviewService()

    listing = service.list_responses(provider, survey.survey_id)
    detail = service.get_response(provider, survey.survey_id, 1)

    forbidden = {"response_id", "respondent_id", "device_hash", "timings", "survey_id"}
    assert not forbidden & set(listing)
    assert not forbidden & set(detail)
    for row in listing["rows"]:
        assert not forbidden & set(row)
    for item in detail["answers"]:
        assert not forbidden & set(item)
