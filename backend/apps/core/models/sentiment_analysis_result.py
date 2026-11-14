from django.db import models
from django.utils import timezone

from core.enums import AnalysisStatus, SentimentLabel


class SentimentAnalysisResult(models.Model):
    """Stores sentiment analysis state and output for an open-text answer."""

    result_id = models.BigAutoField(primary_key=True)
    answer = models.OneToOneField(
        "core.Answer",
        on_delete=models.CASCADE,
        related_name="sentiment_analysis_result",
    )
    sentiment_label = models.CharField(
        max_length=16,
        choices=SentimentLabel.choices,
        null=True,
        blank=True,
    )
    sentiment_score = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
    )
    analyzed_at = models.DateTimeField(null=True, blank=True)
    # Worker state. db_default keeps inserts that do not name these columns valid.
    attempts = models.PositiveSmallIntegerField(default=0, db_default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=32, blank=True, default="", db_default="")
    language = models.CharField(max_length=8, blank=True, default="", db_default="")
    model_id = models.CharField(max_length=255, blank=True, default="", db_default="")

    class Meta:
        db_table = "sentiment_analysis_results"
        indexes = [
            models.Index(fields=["status"], name="sent_results_status_idx"),
        ]

    def __str__(self):
        """Return a readable sentiment result label."""
        return f"Sentiment result {self.result_id}"

    def mark_completed(self, label, score, analyzed_at, language="", model_id=""):
        """Store a successful sentiment analysis outcome."""
        self.sentiment_label = label
        self.sentiment_score = score
        self.status = AnalysisStatus.COMPLETED
        self.analyzed_at = analyzed_at
        self.language = language
        self.model_id = model_id
        self.error_code = ""
        self.locked_at = None

    def mark_failed(self, error_code):
        """Record a final failed sentiment analysis attempt with its reason code."""
        self.sentiment_label = None
        self.sentiment_score = None
        self.status = AnalysisStatus.FAILED
        self.analyzed_at = timezone.now()
        self.error_code = error_code
        self.locked_at = None

    def mark_skipped(self, error_code):
        """Record that the answer has nothing the model can analyse."""
        self.sentiment_label = None
        self.sentiment_score = None
        self.status = AnalysisStatus.SKIPPED
        self.error_code = error_code
        self.locked_at = None

    def schedule_retry(self, next_attempt_at):
        """Return the result to the queue until next_attempt_at."""
        self.status = AnalysisStatus.PENDING
        self.next_attempt_at = next_attempt_at
        self.locked_at = None
