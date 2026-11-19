from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.models import Answer, Question, Response, SentimentAnalysisResult, Survey, User
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from core.exceptions import (
    AnalysisBadOutput,
    AnalysisConfigError,
    AnalysisPaymentRequired,
    AnalysisUnavailable,
    SurveyNotFound,
    UnauthorizedAction,
)
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services.analysis_service import AnalysisService

MODEL_ID = "org/sentiment-model"


@pytest.fixture(autouse=True)
def results_open_for_counting_tests(monkeypatch):
    """These tests predate P-20 and read results of surveys with 1 to 4 responses.

    They test counting, so the lock is opened here; it is tested at the real value
    in test_results_lock.py.
    """
    monkeypatch.setattr("services.disclosure.MIN_GROUP_SIZE", 0)


class FakeClient:
    """Returns the queued outcomes in order; an exception instance is raised."""

    model_id = MODEL_ID

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes) or [{"label": "POSITIVE", "score": 0.9}]
        self.calls = []

    def analyze_sentiment(self, text):
        self.calls.append(text)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey(label="worker"):
    provider = create_user(f"provider-{label}@example.com", UserType.SERVICE_PROVIDER)
    return SurveyRepository().save(Survey(provider=provider, title="Survey", description="D"))


def create_question(survey, question_type=QuestionType.OPEN_TEXT, order_index=0):
    return QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Question?",
            question_type=question_type,
            is_required=False,
            order_index=order_index,
        )
    )


def create_answer(survey, text, label=None):
    """Create one response with one open-text answer."""
    label = label or f"r{Response.objects.count()}"
    respondent = create_user(f"respondent-{label}@example.com", UserType.RESPONDENT)
    response = ResponseRepository().save(Response(survey=survey, respondent=respondent))
    question = create_question(survey)
    return ResponseRepository().save_answer(
        Answer(response=response, question=question, answer_value=text)
    )


def create_pending(survey, text="Great service", **fields):
    answer = create_answer(survey, text)
    return AnalysisRepository().save(
        SentimentAnalysisResult(answer=answer, status=AnalysisStatus.PENDING, **fields)
    )


def reload(result):
    return SentimentAnalysisResult.objects.get(pk=result.pk)


# queue_open_text_answers


@pytest.mark.django_db
def test_queue_writes_one_pending_row_per_open_text_answer_with_text():
    survey = create_survey("queue")
    with_text = create_answer(survey, "Great service")
    blank = create_answer(survey, "   ")
    rating_question = create_question(survey, QuestionType.RATING_SCALE, order_index=5)
    rating = ResponseRepository().save_answer(
        Answer(response=with_text.response, question=rating_question, rating_value=4)
    )
    client = FakeClient()

    AnalysisService(analyzer=client).queue_open_text_answers([with_text, blank, rating])

    rows = list(SentimentAnalysisResult.objects.all())
    assert [row.answer_id for row in rows] == [with_text.answer_id]
    assert rows[0].status == AnalysisStatus.PENDING
    assert rows[0].attempts == 0
    assert client.calls == []


# process_pending_batch outcomes


@pytest.mark.django_db
def test_success_stores_label_score_language_and_model_id():
    result = create_pending(create_survey("ok"), "الخدمة ممتازة")
    client = FakeClient({"label": "POSITIVE", "score": 0.95})

    processed = AnalysisService(analyzer=client).process_pending_batch()

    stored = reload(result)
    assert [row.pk for row in processed] == [result.pk]
    assert stored.status == AnalysisStatus.COMPLETED
    assert stored.sentiment_label == SentimentLabel.POSITIVE
    assert stored.sentiment_score == 0.95
    assert stored.analyzed_at is not None
    assert stored.language == "ar"
    assert stored.model_id == MODEL_ID
    assert stored.error_code == ""
    assert stored.locked_at is None
    assert stored.attempts == 1


@pytest.mark.django_db
def test_text_without_letters_is_skipped_without_a_gateway_call():
    result = create_pending(create_survey("skip"), "123 !!!")
    client = FakeClient()

    AnalysisService(analyzer=client).process_pending_batch()

    stored = reload(result)
    assert stored.status == AnalysisStatus.SKIPPED
    assert stored.error_code == "no_text"
    assert stored.locked_at is None
    assert client.calls == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "error_code"),
    [
        (AnalysisPaymentRequired("HTTP 402"), "payment_required"),
        (AnalysisConfigError("HTTP 401"), "config"),
        (AnalysisBadOutput("bad"), "bad_output"),
    ],
    ids=["402", "config", "bad-output"],
)
def test_payment_config_and_bad_output_fail_at_once(error, error_code):
    result = create_pending(create_survey("fail"))

    AnalysisService(analyzer=FakeClient(error)).process_pending_batch()

    stored = reload(result)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_code == error_code
    assert stored.attempts == 1
    assert stored.next_attempt_at is None
    assert stored.locked_at is None


@pytest.mark.django_db
def test_unknown_label_from_the_client_fails_as_bad_output():
    result = create_pending(create_survey("label"))

    AnalysisService(
        analyzer=FakeClient({"label": "MIXED", "score": 0.5})
    ).process_pending_batch()

    stored = reload(result)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_code == "bad_output"


def make_due(result):
    SentimentAnalysisResult.objects.filter(pk=result.pk).update(
        next_attempt_at=timezone.now() - timedelta(seconds=1)
    )


@pytest.mark.django_db
def test_unavailable_twice_then_success():
    result = create_pending(create_survey("retry"))
    client = FakeClient(
        AnalysisUnavailable("timeout"),
        AnalysisUnavailable("HTTP 503"),
        {"label": "NEGATIVE", "score": 0.8},
    )
    service = AnalysisService(analyzer=client)

    before = timezone.now()
    service.process_pending_batch()
    first = reload(result)
    assert first.status == AnalysisStatus.PENDING
    assert first.attempts == 1
    assert first.locked_at is None
    assert timedelta(seconds=29) < first.next_attempt_at - before < timedelta(seconds=40)

    make_due(result)
    before = timezone.now()
    service.process_pending_batch()
    second = reload(result)
    assert second.status == AnalysisStatus.PENDING
    assert second.attempts == 2
    assert timedelta(seconds=119) < second.next_attempt_at - before < timedelta(seconds=130)

    make_due(result)
    service.process_pending_batch()
    third = reload(result)
    assert third.status == AnalysisStatus.COMPLETED
    assert third.sentiment_label == SentimentLabel.NEGATIVE
    assert third.attempts == 3
    assert len(client.calls) == 3


@pytest.mark.django_db
def test_unavailable_three_times_fails_as_unavailable():
    result = create_pending(create_survey("exhaust"))
    service = AnalysisService(analyzer=FakeClient(AnalysisUnavailable("down")))

    for _ in range(3):
        service.process_pending_batch()
        make_due(result)

    stored = reload(result)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_code == "unavailable"
    assert stored.attempts == 3


@pytest.mark.django_db
def test_row_whose_next_attempt_is_not_due_is_not_claimed():
    result = create_pending(
        create_survey("not-due"),
        next_attempt_at=timezone.now() + timedelta(seconds=60),
    )
    client = FakeClient()

    processed = AnalysisService(analyzer=client).process_pending_batch()

    assert processed == []
    assert client.calls == []
    assert reload(result).status == AnalysisStatus.PENDING


@pytest.mark.django_db
def test_fresh_running_row_is_not_claimed():
    answer = create_answer(create_survey("fresh-lock"), "Great service")
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.RUNNING,
            locked_at=timezone.now() - timedelta(minutes=1),
            attempts=1,
        )
    )

    processed = AnalysisService(analyzer=FakeClient()).process_pending_batch()

    assert processed == []


@pytest.mark.django_db
def test_stale_running_row_is_reclaimed():
    answer = create_answer(create_survey("stale"), "Great service")
    result = AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.RUNNING,
            locked_at=timezone.now() - timedelta(minutes=6),
            attempts=1,
        )
    )

    AnalysisService(analyzer=FakeClient()).process_pending_batch()

    stored = reload(result)
    assert stored.status == AnalysisStatus.COMPLETED
    assert stored.attempts == 2


@pytest.mark.django_db
def test_stale_running_row_with_three_attempts_fails_without_a_call():
    answer = create_answer(create_survey("stale-max"), "Great service")
    result = AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.RUNNING,
            locked_at=timezone.now() - timedelta(minutes=6),
            attempts=3,
        )
    )
    client = FakeClient()

    processed = AnalysisService(analyzer=client).process_pending_batch()

    stored = reload(result)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_code == "unavailable"
    assert stored.attempts == 3
    assert stored.locked_at is None
    assert client.calls == []
    assert [row.pk for row in processed] == [result.pk]


@pytest.mark.django_db
def test_batch_claims_at_most_the_limit_in_result_id_order():
    survey = create_survey("limit")
    results = [create_pending(survey, f"Answer {index}") for index in range(3)]

    processed = AnalysisService(analyzer=FakeClient()).process_pending_batch(limit=2)

    assert [row.pk for row in processed] == [results[0].pk, results[1].pk]
    assert reload(results[2]).status == AnalysisStatus.PENDING


def test_worker_constants():
    assert AnalysisService.BATCH_SIZE == 8
    assert AnalysisService.LOCK_TIMEOUT == timedelta(minutes=5)
    assert AnalysisService.RETRY_DELAYS_SECONDS == (30, 120)
    assert AnalysisService.MAX_ATTEMPTS == 3


# Due time, overdue hint (W-05a, D-151 (3)) and retry_failed


def create_result(survey, status, text="Text", submitted_ago=None, **fields):
    """Create one result; submitted_ago moves its response's submit time into the past."""
    answer = create_answer(survey, text)
    if submitted_ago is not None:
        Response.objects.filter(pk=answer.response_id).update(
            submitted_at=timezone.now() - submitted_ago
        )
    return AnalysisRepository().save(
        SentimentAnalysisResult(answer=answer, status=status, **fields)
    )


@pytest.mark.django_db
def test_oldest_due_at_takes_next_attempt_over_submit_time():
    survey = create_survey("due")
    now = timezone.now()
    retry_at = now + timedelta(minutes=1)
    # Submitted an hour ago, but its retry is due in a minute.
    create_result(
        survey, AnalysisStatus.PENDING, submitted_ago=timedelta(hours=1), next_attempt_at=retry_at
    )
    # Submitted ten minutes ago with no retry time: due at its submit time.
    plain = create_result(survey, AnalysisStatus.PENDING, submitted_ago=timedelta(minutes=10))

    due = AnalysisRepository().oldest_due_at(survey.survey_id)

    assert due == Response.objects.get(pk=plain.answer.response_id).submitted_at


@pytest.mark.django_db
def test_oldest_due_at_ignores_other_surveys_and_non_pending_rows():
    survey = create_survey("due-own")
    retry_at = timezone.now() + timedelta(minutes=3)
    create_result(survey, AnalysisStatus.PENDING, next_attempt_at=retry_at)
    for status in (
        AnalysisStatus.RUNNING,
        AnalysisStatus.FAILED,
        AnalysisStatus.COMPLETED,
        AnalysisStatus.SKIPPED,
    ):
        create_result(survey, status, submitted_ago=timedelta(hours=2))
    create_result(
        create_survey("due-other"), AnalysisStatus.PENDING, submitted_ago=timedelta(hours=2)
    )

    assert AnalysisRepository().oldest_due_at(survey.survey_id) == retry_at


@pytest.mark.django_db
def test_oldest_due_at_is_none_without_pending_rows():
    survey = create_survey("due-none")
    create_result(survey, AnalysisStatus.COMPLETED)

    assert AnalysisRepository().oldest_due_at(survey.survey_id) is None


@pytest.mark.django_db
def test_has_stale_running_only_for_a_running_row_locked_before_the_cut_off():
    survey = create_survey("stale")
    now = timezone.now()
    cut_off = now - timedelta(minutes=5)
    create_result(survey, AnalysisStatus.RUNNING, locked_at=now - timedelta(minutes=1))
    create_result(survey, AnalysisStatus.PENDING, locked_at=now - timedelta(minutes=9))
    create_result(
        create_survey("stale-other"), AnalysisStatus.RUNNING, locked_at=now - timedelta(minutes=9)
    )
    repository = AnalysisRepository()

    assert repository.has_stale_running(survey.survey_id, cut_off) is False

    create_result(survey, AnalysisStatus.RUNNING, locked_at=now - timedelta(minutes=6))

    assert repository.has_stale_running(survey.survey_id, cut_off) is True


@pytest.mark.django_db
def test_reset_failed_sets_next_attempt_to_the_given_now():
    survey = create_survey("reset-now")
    failed = create_result(survey, AnalysisStatus.FAILED, attempts=3, error_code="unavailable")
    now = timezone.now()

    assert AnalysisRepository().reset_failed(survey.survey_id, now) == 1

    assert reload(failed).next_attempt_at == now


def test_overdue_constant():
    assert AnalysisService.OVERDUE_AFTER == timedelta(minutes=2)


def overdue(survey):
    return AnalysisService(analyzer=FakeClient()).get_survey_results(
        survey.provider, survey.survey_id
    )["analysis_overdue"]


@pytest.mark.django_db
def test_row_due_30_seconds_ago_is_not_overdue():
    survey = create_survey("overdue-30s")
    create_result(survey, AnalysisStatus.PENDING, submitted_ago=timedelta(seconds=30))

    assert overdue(survey) is False


@pytest.mark.django_db
def test_row_due_3_minutes_ago_is_overdue():
    survey = create_survey("overdue-3m")
    create_result(survey, AnalysisStatus.PENDING, submitted_ago=timedelta(minutes=3))

    assert overdue(survey) is True


@pytest.mark.django_db
def test_running_row_locked_6_minutes_ago_is_overdue():
    survey = create_survey("overdue-lock")
    create_result(
        survey, AnalysisStatus.RUNNING, locked_at=timezone.now() - timedelta(minutes=6)
    )

    assert overdue(survey) is True


@pytest.mark.django_db
def test_old_answer_with_a_retry_in_the_future_is_not_overdue():
    survey = create_survey("overdue-retry")
    create_result(
        survey,
        AnalysisStatus.PENDING,
        submitted_ago=timedelta(hours=1),
        attempts=1,
        next_attempt_at=timezone.now() + timedelta(seconds=30),
    )

    assert overdue(survey) is False


@pytest.mark.django_db
def test_failed_reasons_group_codes_map_none_to_empty_and_order_by_count():
    survey = create_survey("reasons")
    for code in ["unavailable", "payment_required", "payment_required", "", "config", "config"]:
        create_result(survey, AnalysisStatus.FAILED, error_code=code)
    create_result(survey, AnalysisStatus.SKIPPED, error_code="no_text")

    results = AnalysisService(analyzer=FakeClient()).get_survey_results(
        survey.provider, survey.survey_id
    )

    assert results["failed_reasons"] == [
        {"code": "config", "count": 2},
        {"code": "payment_required", "count": 2},
        {"code": "", "count": 1},
        {"code": "unavailable", "count": 1},
    ]
    assert results["failed_count"] == 6


@pytest.mark.django_db
def test_survey_results_report_waiting_and_skipped_counts():
    survey = create_survey("results")
    create_result(survey, AnalysisStatus.PENDING)
    create_result(survey, AnalysisStatus.RUNNING)
    create_result(survey, AnalysisStatus.SKIPPED)

    results = AnalysisService(analyzer=FakeClient()).get_survey_results(
        survey.provider, survey.survey_id
    )

    assert results["waiting_count"] == 2
    assert results["skipped_count"] == 1
    assert results["failed_count"] == 0
    assert results["positive_count"] == 0


@pytest.mark.django_db
def test_retry_failed_resets_only_failed_rows_of_the_survey():
    survey = create_survey("retry-failed")
    failed = create_result(survey, AnalysisStatus.FAILED, submitted_ago=timedelta(hours=1))
    SentimentAnalysisResult.objects.filter(pk=failed.pk).update(
        attempts=3, error_code="unavailable", next_attempt_at=timezone.now()
    )
    completed = create_result(survey, AnalysisStatus.COMPLETED)
    skipped = create_result(survey, AnalysisStatus.SKIPPED)
    other_failed = create_result(create_survey("retry-other"), AnalysisStatus.FAILED)
    service = AnalysisService(analyzer=FakeClient())
    before = timezone.now()

    reset = service.retry_failed(survey.provider, survey.survey_id)

    assert reset == 1
    stored = reload(failed)
    assert stored.status == AnalysisStatus.PENDING
    assert stored.attempts == 0
    # D-158 (2e): due now, so an old answer is not overdue the moment it is retried.
    assert before <= stored.next_attempt_at <= timezone.now()
    assert stored.error_code == ""
    assert overdue(survey) is False
    assert reload(completed).status == AnalysisStatus.COMPLETED
    assert reload(skipped).status == AnalysisStatus.SKIPPED
    assert reload(other_failed).status == AnalysisStatus.FAILED


@pytest.mark.django_db
def test_retry_failed_rejects_a_provider_who_does_not_own_the_survey():
    survey = create_survey("retry-owner")
    failed = create_result(survey, AnalysisStatus.FAILED)
    other = create_user("other-retry@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        AnalysisService(analyzer=FakeClient()).retry_failed(other, survey.survey_id)

    assert reload(failed).status == AnalysisStatus.FAILED


@pytest.mark.django_db
def test_retry_failed_rejects_a_respondent_and_a_missing_survey():
    survey = create_survey("retry-role")
    respondent = create_user("respondent-retry@example.com", UserType.RESPONDENT)
    service = AnalysisService(analyzer=FakeClient())

    with pytest.raises(UnauthorizedAction):
        service.retry_failed(respondent, survey.survey_id)
    with pytest.raises(SurveyNotFound):
        service.retry_failed(survey.provider, 999999)
