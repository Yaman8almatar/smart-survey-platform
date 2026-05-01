from django.conf import settings
from django.db import models

from core.enums import QuestionType


class Response(models.Model):
    """Represents one respondent submission for one survey."""

    response_id = models.BigAutoField(primary_key=True)
    survey = models.ForeignKey(
        "core.Survey",
        on_delete=models.CASCADE,
        related_name="responses",
    )
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "responses"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "respondent"],
                name="unique_response_per_survey_respondent",
            )
        ]

    def __str__(self):
        """Return a readable response label."""
        return f"Response {self.response_id} for {self.survey}"

    def add_answer(self, answer):
        """Attach an answer object to this response."""
        answer.response = self
        return answer

    def has_open_text_answers(self):
        """Return whether this response includes open-text answers."""
        return self.answers.filter(question__question_type=QuestionType.OPEN_TEXT).exists()
