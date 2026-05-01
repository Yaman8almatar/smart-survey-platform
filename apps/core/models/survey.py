from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.enums import SurveyStatus, UserType


class Survey(models.Model):
    """Represents a survey created and managed by a service provider."""

    survey_id = models.BigAutoField(primary_key=True)
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="surveys",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=SurveyStatus.choices,
        default=SurveyStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "surveys"

    def __str__(self):
        """Return the survey title."""
        return self.title

    def clean(self):
        """Validate that the survey owner is a service provider."""
        if self.provider_id and self.provider.user_type != UserType.SERVICE_PROVIDER:
            raise ValidationError(
                {"provider": "Survey providers must be service provider users."}
            )

    def publish(self):
        """Move the survey to the published state."""
        self.status = SurveyStatus.PUBLISHED
        self.published_at = timezone.now()

    def close(self):
        """Move the survey to the closed state."""
        self.status = SurveyStatus.CLOSED
        self.closed_at = timezone.now()

    def can_edit(self):
        """Return whether the survey can still be edited."""
        return self.status == SurveyStatus.DRAFT

    def can_delete(self):
        """Return whether the survey can still be deleted."""
        return self.status == SurveyStatus.DRAFT

    def can_accept_responses(self):
        """Return whether respondents can submit answers."""
        return self.status == SurveyStatus.PUBLISHED
