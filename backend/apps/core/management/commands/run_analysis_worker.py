import time
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from core.enums import AnalysisStatus
from services.analysis_service import AnalysisService


class Command(BaseCommand):
    """Analyses PENDING sentiment results in small batches (T-9)."""

    help = "Analyse PENDING sentiment results. Runs until Ctrl+C, or one batch with --once."

    def add_arguments(self, parser):
        """Declare the worker options."""
        parser.add_argument("--once", action="store_true", help="Run one batch and exit.")
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
        """Run batches until stopped, or one batch with --once."""
        batch_size = options["batch_size"]
        interval = options["interval"]
        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1.")
        if interval < 0:
            raise CommandError("--interval must not be negative.")

        service = AnalysisService()
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
