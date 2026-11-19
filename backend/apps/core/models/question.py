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
    # FR-04 attention check (P-03). Neither field ever leaves the server (D-046 rule 4).
    is_attention_check = models.BooleanField(default=False, db_default=False)
    expected_option = models.ForeignKey(
        "core.QuestionOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    expected_rating = models.PositiveSmallIntegerField(null=True, blank=True)

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
