from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Value

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
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    # FR-04 include/exclude decision; unused until TASK-42.
    is_excluded = models.BooleanField(default=False, db_default=False)
    excluded_at = models.DateTimeField(null=True, blank=True)
    # FR-04 snapshot: the respondent's profile as it was at submit (P-08). Lengths match
    # RespondentProfile; no choices, so a later list change never rewrites history.
    snap_age = models.PositiveSmallIntegerField(null=True, blank=True)
    snap_gender = models.CharField(max_length=16, blank=True, default="", db_default="")
    snap_region = models.CharField(max_length=32, blank=True, default="", db_default="")
    snap_education = models.CharField(max_length=32, blank=True, default="", db_default="")
    snap_occupation = models.CharField(max_length=32, blank=True, default="", db_default="")
    snap_marital_status = models.CharField(
        max_length=32, blank=True, default="", db_default=""
    )
    snap_interests = ArrayField(
        models.CharField(max_length=32),
        default=list,
        blank=True,
        db_default=Value([], output_field=ArrayField(models.CharField(max_length=32))),
    )

    class Meta:
        db_table = "responses"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "respondent"],
                name="unique_response_per_survey_respondent",
            )
        ]
        indexes = [
            models.Index(fields=["submitted_at"], name="responses_sub_at_idx"),
            models.Index(fields=["respondent", "submitted_at"], name="responses_resp_sub_idx"),
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
