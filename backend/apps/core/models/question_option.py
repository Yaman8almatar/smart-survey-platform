from django.db import models


class QuestionOption(models.Model):
    """Represents one selectable option for a multiple-choice question."""

    option_id = models.BigAutoField(primary_key=True)
    question = models.ForeignKey(
        "core.Question",
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=255)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "question_options"
        ordering = ["order_index", "option_id"]

    def __str__(self):
        """Return the option text."""
        return self.option_text
