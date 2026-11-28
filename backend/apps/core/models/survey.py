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
    # FR-03 (P-19): respondents matching the criteria when the survey was published,
    # unbanded. Every display of it goes through services.disclosure.band.
    reach_at_publish = models.PositiveIntegerField(null=True, blank=True)
    # FR-16: each respondent sees a fixed order of their own (services.presentation_order).
    shuffle_questions = models.BooleanField(default=False, db_default=False)
    shuffle_options = models.BooleanField(default=False, db_default=False)
    # FR-12: an admin approves (publishes) or rejects (back to draft, with a reason).
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_surveys",
    )
    rejection_reason = models.CharField(
        max_length=1000, blank=True, default="", db_default=""
    )
    # FR-11: an optional schedule and response limit; empty means none.
    opens_on = models.DateField(null=True, blank=True)
    closes_on = models.DateField(null=True, blank=True)
    target_responses = models.PositiveIntegerField(null=True, blank=True)
    # FR-10: random token of the invitation link; set the first time the provider opens Share.
    invite_token = models.CharField(max_length=32, unique=True, null=True, blank=True)

    class Meta:
        db_table = "surveys"
        indexes = [
            models.Index(fields=["status"], name="surveys_status_idx"),
            models.Index(fields=["status", "published_at"], name="surveys_status_pub_idx"),
        ]

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

    def submit_for_review(self):
        """Lock the survey until an admin approves or rejects it; clear the last review."""
        self.status = SurveyStatus.PENDING_REVIEW
        self.submitted_at = timezone.now()
        self.rejection_reason = ""
        self.reviewed_at = None
        self.reviewed_by = None

    def approve(self, admin_user):
        """Record the approving admin, then publish the survey."""
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.publish()

    def reject(self, admin_user, reason):
        """Return the survey to its provider as a draft with the admin's reason."""
        self.status = SurveyStatus.DRAFT
        self.rejection_reason = reason
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()

    def is_pending_review(self):
        """Return whether the survey is waiting for an admin's review."""
        return self.status == SurveyStatus.PENDING_REVIEW

    def close(self):
        """Move the survey to the closed state."""
        self.status = SurveyStatus.CLOSED
        self.closed_at = timezone.now()

    def pause(self):
        """Stop taking responses until the provider resumes the survey."""
        self.status = SurveyStatus.PAUSED

    def resume(self):
        """Take responses again after a pause."""
        self.status = SurveyStatus.PUBLISHED

    def is_open_on(self, day):
        """Return whether the survey is published and inside its schedule on day."""
        return (
            self.status == SurveyStatus.PUBLISHED
            and (self.opens_on is None or self.opens_on <= day)
            and (self.closes_on is None or self.closes_on >= day)
        )

    def has_passed_closing(self, day):
        """Return whether the survey's closing date is before day."""
        return self.closes_on is not None and self.closes_on < day

    def can_edit(self):
        """Return whether the survey can still be edited."""
        return self.status == SurveyStatus.DRAFT

    def can_delete(self):
        """Return whether the survey can still be deleted."""
        return self.status in {SurveyStatus.DRAFT, SurveyStatus.CLOSED}

    def can_accept_responses(self):
        """Return whether respondents can submit answers."""
        return self.status == SurveyStatus.PUBLISHED
