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

    class Meta:
        db_table = "sentiment_analysis_results"

    def __str__(self):
        """Return a readable sentiment result label."""
        return f"Sentiment result {self.result_id}"

    def mark_completed(self, label, score, analyzed_at):
        """Store a successful sentiment analysis outcome."""
        self.sentiment_label = label
        self.sentiment_score = score
        self.status = AnalysisStatus.COMPLETED
        self.analyzed_at = analyzed_at

    def mark_failed(self):
        """Record a failed sentiment analysis attempt."""
        self.sentiment_label = None
        self.sentiment_score = None
        self.status = AnalysisStatus.FAILED
        self.analyzed_at = timezone.now()
