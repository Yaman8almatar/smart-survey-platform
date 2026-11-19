import time
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.enums import AnalysisStatus
from core.exceptions import ExternalAnalysisServiceError
from infrastructure.sentiment_analyzer import build_analyzer
from services.analysis_service import AnalysisService

# Smoke test for --check, not an evaluation: only valid labels and scores are asserted.
CHECK_SENTENCES = (
    ("en", "The staff were helpful and the service was excellent."),
    ("ar", "الخدمة سيئة جداً ولن أعود مرة أخرى."),
    ("en", "The meeting is on Tuesday at ten."),
)
VALID_LABELS = {"POSITIVE", "NEUTRAL", "NEGATIVE"}


class Command(BaseCommand):
    """Analyses PENDING sentiment results in small batches (T-9)."""

    help = (
        "Analyse PENDING sentiment results. Runs until Ctrl+C, one batch with --once, "
        "or labels three fixed sentences and exits with --check."
    )

    def add_arguments(self, parser):
        """Declare the worker options."""
        parser.add_argument("--once", action="store_true", help="Run one batch and exit.")
        parser.add_argument(
            "--check",
            action="store_true",
            help="Label three fixed sentences with the configured analyzer and exit; no database row is touched.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=2,
            help="Seconds to wait after an empty batch (default 2).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=AnalysisService.BATCH_SIZE,
            help=f"Results per batch (default {AnalysisService.BATCH_SIZE}).",
        )

    def handle(self, *args, **options):
        """Run batches until stopped, one batch with --once, or the analyzer check."""
        if options["check"]:
            self._check()
            return

        batch_size = options["batch_size"]
        interval = options["interval"]
        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1.")
        if interval < 0:
            raise CommandError("--interval must not be negative.")

        service = AnalysisService()
        if not options["once"]:
            self.stdout.write(
                f"Analyzer {settings.SENTIMENT_ANALYZER}, model {service.analyzer.model_id}."
            )
        try:
            while True:
                results = service.process_pending_batch(limit=batch_size)
                if results:
                    self.stdout.write(self._batch_line(results))
                if options["once"]:
                    if not results:
                        self.stdout.write("No pending sentiment results.")
                    return
                if not results:
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")

    def _check(self):
        """Label the fixed sentences and print label, score and milliseconds for each."""
        analyzer = build_analyzer()
        self.stdout.write(f"Analyzer {settings.SENTIMENT_ANALYZER}, model {analyzer.model_id}.")
        for number, (language, text) in enumerate(CHECK_SENTENCES, start=1):
            start = time.perf_counter()
            try:
                result = analyzer.analyze_sentiment(text)
            except ExternalAnalysisServiceError as exc:
                raise CommandError(f"Analyzer error {exc.error_code}: {exc}") from exc
            ms = (time.perf_counter() - start) * 1000
            label, score = result.get("label"), result.get("score")
            if label not in VALID_LABELS or not isinstance(score, float) or not 0 <= score <= 1:
                raise CommandError(f"Analyzer returned an invalid result for sentence {number}: {result!r}")
            note = " (includes the model load)" if number == 1 else ""
            self.stdout.write(f"{number} [{language}] {label} {score:.3f} {ms:.0f} ms{note}")

    def _batch_line(self, results):
        """Return one line with the count of each outcome in the batch."""
        counts = Counter(str(result.status) for result in results)
        return (
            f"Batch of {len(results)}: "
            f"completed {counts[AnalysisStatus.COMPLETED]}, "
            f"skipped {counts[AnalysisStatus.SKIPPED]}, "
            f"failed {counts[AnalysisStatus.FAILED]}, "
            f"retry later {counts[AnalysisStatus.PENDING]}"
        )
