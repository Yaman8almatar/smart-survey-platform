from django.db import models

from core.enums import QuestionType


class Answer(models.Model):
    """Stores one answer using the field required by the question type."""

    answer_id = models.BigAutoField(primary_key=True)
    response = models.ForeignKey(
        "core.Response",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "core.Question",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    answer_value = models.TextField(null=True, blank=True)
    rating_value = models.IntegerField(null=True, blank=True)
    selected_option = models.ForeignKey(
        "core.QuestionOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="answers",
    )

    class Meta:
        db_table = "answers"

    def __str__(self):
        """Return a readable answer label."""
        return f"Answer {self.answer_id}"

    def is_textual(self):
        """Return whether this answer belongs to an open-text question."""
        return self.question.question_type == QuestionType.OPEN_TEXT

    def is_rating_based(self):
        """Return whether this answer belongs to a rating-scale question."""
        return self.question.question_type == QuestionType.RATING_SCALE

    def is_option_based(self):
        """Return whether this answer belongs to a multiple-choice question."""
        return self.question.question_type == QuestionType.MULTIPLE_CHOICE

    def requires_sentiment_analysis(self):
        """Return whether this answer should be analyzed for sentiment."""
        return self.is_textual()
