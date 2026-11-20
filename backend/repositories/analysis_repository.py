from django.db import transaction
from django.db.models import Min, Q
from django.db.models.functions import Coalesce

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus


class AnalysisRepository:
    """Provides database access for sentiment analysis results."""

    def save(self, result):
        """Persist a sentiment analysis result."""
        result.save()
        return result

    def create_pending(self, answers):
        """Store one PENDING result for each given answer."""
        return SentimentAnalysisResult.objects.bulk_create(
            [
                SentimentAnalysisResult(answer=answer, status=AnalysisStatus.PENDING)
                for answer in answers
            ]
        )

    def find_by_answer_id(self, answer_id):
        """Return the sentiment result for one answer."""
        return SentimentAnalysisResult.objects.filter(answer_id=answer_id).first()

    def find_by_survey_id(self, survey_id):
        """Return sentiment results produced by answers for a survey."""
        return SentimentAnalysisResult.objects.filter(
            answer__response__survey_id=survey_id
        ).select_related("answer", "answer__response", "answer__response__survey")

    def find_statuses_by_survey_id(self, survey_id):
        """Return (response_id, status, sentiment_label) of every result of a survey, in one query.

        Excluded responses are included.
        """
        return list(
            SentimentAnalysisResult.objects.filter(
                answer__response__survey_id=survey_id
            ).values_list("answer__response_id", "status", "sentiment_label")
        )

    def find_by_response_id(self, response_id):
        """Return {answer_id: (status, sentiment_label)} of one response's results, in one query."""
        return {
            answer_id: (status, label)
            for answer_id, status, label in SentimentAnalysisResult.objects.filter(
                answer__response_id=response_id
            ).values_list("answer_id", "status", "sentiment_label")
        }

    def find_included_by_survey_id(self, survey_id):
        """Return the sentiment results of a survey's responses that are not excluded."""
        return self.find_by_survey_id(survey_id).filter(answer__response__is_excluded=False)

    def claim_batch(self, limit, now, stale_before, max_attempts, expired_error_code):
        """Lock up to limit due rows and mark them RUNNING; return (claimed, expired).

        Due rows are PENDING rows whose next attempt is due and RUNNING rows whose
        lock is older than stale_before. A stale row that already used max_attempts
        becomes FAILED instead of being claimed. Rows locked by another claim are
        skipped, so two workers never get the same row.
        """
        due = Q(status=AnalysisStatus.PENDING) & (
            Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)
        )
        stale = Q(status=AnalysisStatus.RUNNING, locked_at__lt=stale_before)

        with transaction.atomic():
            rows = list(
                SentimentAnalysisResult.objects.select_for_update(
                    skip_locked=True,
                    of=("self",),
                )
                .select_related("answer")
                .filter(due | stale)
                .order_by("result_id")[:limit]
            )

            claimed = []
            expired = []
            for row in rows:
                if row.status == AnalysisStatus.RUNNING and row.attempts >= max_attempts:
                    row.mark_failed(expired_error_code)
                    expired.append(row)
                    continue

                row.status = AnalysisStatus.RUNNING
                row.locked_at = now
                row.attempts += 1
                claimed.append(row)

            if rows:
                SentimentAnalysisResult.objects.bulk_update(
                    rows,
                    [
                        "status",
                        "locked_at",
                        "attempts",
                        "error_code",
                        "sentiment_label",
                        "sentiment_score",
                        "analyzed_at",
                    ],
                )

        return claimed, expired

    def oldest_due_at(self, survey_id):
        """Return the earliest due time of the survey's PENDING results, or None.

        A row is due at its next_attempt_at when one is set (a retry or a provider
        reset), otherwise at the submit time of its response.
        """
        return (
            SentimentAnalysisResult.objects.filter(
                answer__response__survey_id=survey_id,
                status=AnalysisStatus.PENDING,
            )
            .annotate(due_at=Coalesce("next_attempt_at", "answer__response__submitted_at"))
            .aggregate(oldest=Min("due_at"))["oldest"]
        )

    def has_stale_running(self, survey_id, stale_before):
        """Return whether a RUNNING result of the survey is locked since before stale_before."""
        return SentimentAnalysisResult.objects.filter(
            answer__response__survey_id=survey_id,
            status=AnalysisStatus.RUNNING,
            locked_at__lt=stale_before,
        ).exists()

    def reset_failed(self, survey_id, now):
        """Return the FAILED results of a survey to the queue, due at now; return how many."""
        return SentimentAnalysisResult.objects.filter(
            answer__response__survey_id=survey_id,
            status=AnalysisStatus.FAILED,
        ).update(
            status=AnalysisStatus.PENDING,
            attempts=0,
            next_attempt_at=now,
            locked_at=None,
            error_code="",
            analyzed_at=None,
        )

    def update(self, result):
        """Persist changes to a sentiment analysis result."""
        result.save()
        return result
