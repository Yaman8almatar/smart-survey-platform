from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus
from core.exceptions import AnalysisUnavailable
from services.analysis_service import AnalysisService
from tests.services.test_analysis_worker import FakeClient, create_pending, create_survey


def use_fake_client(monkeypatch, client):
    # A subclass keeps the class constants (BATCH_SIZE) the command reads for its options.
    class FakeClientAnalysisService(AnalysisService):
        def __init__(self, **kwargs):
            super().__init__(huggingface_client=client, **kwargs)

    monkeypatch.setattr(
        "apps.core.management.commands.run_analysis_worker.AnalysisService",
        FakeClientAnalysisService,
    )


@pytest.mark.django_db
def test_once_runs_one_batch_and_prints_the_outcome_counts(monkeypatch):
    survey = create_survey("command")
    completed = create_pending(survey, "Great service")
    skipped = create_pending(survey, "123 !!!")
    retried = create_pending(survey, "Slow delivery")
    client = FakeClient({"label": "POSITIVE", "score": 0.9}, AnalysisUnavailable("down"))
    use_fake_client(monkeypatch, client)
    out = StringIO()

    call_command("run_analysis_worker", "--once", stdout=out)

    assert out.getvalue().strip() == (
        "Batch of 3: completed 1, skipped 1, failed 0, retry later 1"
    )
    statuses = {
        row.pk: row.status for row in SentimentAnalysisResult.objects.all()
    }
    assert statuses == {
        completed.pk: AnalysisStatus.COMPLETED,
        skipped.pk: AnalysisStatus.SKIPPED,
        retried.pk: AnalysisStatus.PENDING,
    }


@pytest.mark.django_db
def test_once_respects_the_batch_size(monkeypatch):
    survey = create_survey("command-size")
    for index in range(3):
        create_pending(survey, f"Answer {index}")
    use_fake_client(monkeypatch, FakeClient())
    out = StringIO()

    call_command("run_analysis_worker", "--once", "--batch-size", "2", stdout=out)

    assert out.getvalue().startswith("Batch of 2:")
    assert SentimentAnalysisResult.objects.filter(status=AnalysisStatus.PENDING).count() == 1


@pytest.mark.django_db
def test_once_with_nothing_pending_says_so(monkeypatch):
    use_fake_client(monkeypatch, FakeClient())
    out = StringIO()

    call_command("run_analysis_worker", "--once", stdout=out)

    assert out.getvalue().strip() == "No pending sentiment results."


def test_batch_size_below_one_is_refused():
    with pytest.raises(CommandError):
        call_command("run_analysis_worker", "--once", "--batch-size", "0")
