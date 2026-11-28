from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus
from core.exceptions import AnalysisConfigError, AnalysisUnavailable
from services.analysis_service import AnalysisService
from tests.services.test_analysis_worker import FakeClient, create_pending, create_survey


def use_fake_client(monkeypatch, client):
    # A subclass keeps the class constants (BATCH_SIZE) the command reads for its options.
    class FakeClientAnalysisService(AnalysisService):
        def __init__(self, **kwargs):
            super().__init__(analyzer=client, **kwargs)

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


def use_check_analyzer(monkeypatch, settings, analyzer):
    settings.SENTIMENT_ANALYZER = "local"
    monkeypatch.setattr(
        "apps.core.management.commands.run_analysis_worker.build_analyzer", lambda: analyzer
    )


@pytest.mark.django_db
def test_check_labels_three_sentences_and_touches_no_row(monkeypatch, settings):
    pending = create_pending(create_survey("check"), "Great service")
    client = FakeClient({"label": "POSITIVE", "score": 0.9})
    use_check_analyzer(monkeypatch, settings, client)
    out = StringIO()

    call_command("run_analysis_worker", "--check", stdout=out)

    lines = out.getvalue().strip().splitlines()
    assert lines[0] == "Analyzer local, model org/sentiment-model."
    assert len(lines) == 4
    for number, line in enumerate(lines[1:], start=1):
        assert line.startswith(f"{number} [")
        assert " POSITIVE 0.900 " in line
        assert " ms" in line
    assert len(client.calls) == 3
    assert SentimentAnalysisResult.objects.count() == 1
    assert SentimentAnalysisResult.objects.get(pk=pending.pk).status == AnalysisStatus.PENDING


def test_check_with_a_failing_analyzer_exits_with_a_command_error(monkeypatch, settings):
    use_check_analyzer(monkeypatch, settings, FakeClient(AnalysisConfigError("weights refused")))

    with pytest.raises(CommandError, match="config: weights refused"):
        call_command("run_analysis_worker", "--check", stdout=StringIO())


def test_check_refuses_an_invalid_label_or_score(monkeypatch, settings):
    use_check_analyzer(monkeypatch, settings, FakeClient({"label": "MIXED", "score": 1.5}))

    with pytest.raises(CommandError, match="invalid result"):
        call_command("run_analysis_worker", "--check", stdout=StringIO())


def test_the_running_worker_prints_its_adapter_and_model_first(monkeypatch, settings):
    settings.SENTIMENT_ANALYZER = "local"
    use_fake_client(monkeypatch, FakeClient())
    monkeypatch.setattr(AnalysisService, "process_pending_batch", lambda self, limit: [])

    def stop(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("apps.core.management.commands.run_analysis_worker.time.sleep", stop)
    out = StringIO()

    call_command("run_analysis_worker", stdout=out)

    assert out.getvalue().strip().splitlines() == [
        "Analyzer local, model org/sentiment-model.",
        "Worker stopped.",
    ]
