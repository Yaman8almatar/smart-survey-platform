from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.enums import Gender, UserType


class RespondentProfile(models.Model):
    """Stores respondent demographic data used for survey eligibility."""

    profile_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="respondent_profile",
    )
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=16, choices=Gender.choices)
    region = models.CharField(max_length=255)
    interests = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "respondent_profiles"

    def __str__(self):
        """Return a readable profile label."""
        return f"Profile for {self.user}"

    def clean(self):
        """Validate respondent-only ownership and profile gender rules."""
        errors = {}

        if self.user_id and self.user.user_type != UserType.RESPONDENT:
            errors["user"] = "Respondent profiles can only belong to respondent users."

        if self.gender == Gender.ANY:
            errors["gender"] = "Gender.ANY is not allowed for respondent profiles."

        if errors:
            raise ValidationError(errors)

    def update_profile(self, age, gender, region, interests):
        """Update demographic values used for targeting."""
        self.age = age
        self.gender = gender
        self.region = region
        self.interests = interests

    def is_complete(self):
        """Return whether all required demographic fields are present."""
        return all([self.age, self.gender, self.region, self.interests])
