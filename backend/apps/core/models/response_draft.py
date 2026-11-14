from django.conf import settings
from django.db import models


class ResponseDraft(models.Model):
    """Holds a respondent's unsent answers for one survey."""

    draft_id = models.BigAutoField(primary_key=True)
    survey = models.ForeignKey(
        "core.Survey",
        on_delete=models.CASCADE,
        related_name="drafts",
    )
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="response_drafts",
    )
    answers = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "response_drafts"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "respondent"],
                name="unique_draft_per_survey_respondent",
            )
        ]

    def __str__(self):
        """Return a readable draft label."""
        return f"Draft {self.draft_id} for {self.survey}"
