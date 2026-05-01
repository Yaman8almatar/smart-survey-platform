from django.db import models

from core.enums import QuestionType


class Question(models.Model):
    """Represents one survey question and its answer type."""

    question_id = models.BigAutoField(primary_key=True)
    survey = models.ForeignKey(
        "core.Survey",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=32, choices=QuestionType.choices)
    is_required = models.BooleanField(default=True)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "questions"
        ordering = ["order_index", "question_id"]

    def __str__(self):
        """Return the question text."""
        return self.question_text

    def is_choice_based(self):
        """Return whether the question uses predefined options."""
        return self.question_type == QuestionType.MULTIPLE_CHOICE

    def is_open_text(self):
        """Return whether the question expects a text answer."""
        return self.question_type == QuestionType.OPEN_TEXT
