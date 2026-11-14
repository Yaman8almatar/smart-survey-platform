import threading
from datetime import timedelta

import pytest
from django.db import connection, transaction
from django.utils import timezone

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus
from repositories.analysis_repository import AnalysisRepository
from tests.services.test_analysis_worker import create_answer, create_pending, create_survey


def claim(repository, limit):
    now = timezone.now()
    claimed, _ = repository.claim_batch(
        limit=limit,
        now=now,
        stale_before=now - timedelta(minutes=5),
        max_attempts=3,
        expired_error_code="unavailable",
    )
    return [row.pk for row in claimed]


@pytest.mark.django_db(transaction=True)
def test_second_claim_skips_rows_locked_by_an_open_first_claim():
    survey = create_survey("skip-locked")
    rows = [create_pending(survey, f"Answer {index}") for index in range(3)]
    repository = AnalysisRepository()
    second_claim = []

    def claim_from_another_connection():
        try:
            second_claim.extend(claim(AnalysisRepository(), limit=8))
        finally:
            connection.close()

    with transaction.atomic():
        # The first claim's locks stay held until this outer transaction ends.
        first_claim = claim(repository, limit=2)
        thread = threading.Thread(target=claim_from_another_connection)
        thread.start()
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert first_claim == [rows[0].pk, rows[1].pk]
    assert second_claim == [rows[2].pk]
    assert set(first_claim).isdisjoint(second_claim)
    assert all(
        row.status == AnalysisStatus.RUNNING and row.attempts == 1
        for row in SentimentAnalysisResult.objects.all()
    )


@pytest.mark.django_db
def test_raw_insert_without_the_new_columns_uses_the_database_defaults():
    answer = create_answer(create_survey("raw-insert"), "Great service")

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO sentiment_analysis_results (answer_id, status) VALUES (%s, %s)",
            [answer.answer_id, AnalysisStatus.PENDING.value],
        )

    stored = SentimentAnalysisResult.objects.get(answer=answer)
    assert stored.attempts == 0
    assert stored.error_code == ""
    assert stored.language == ""
    assert stored.model_id == ""
    assert stored.next_attempt_at is None
    assert stored.locked_at is None
