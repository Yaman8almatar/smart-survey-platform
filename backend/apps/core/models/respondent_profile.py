from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from core.enums import (
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    UserType,
)


class RespondentProfile(models.Model):
    """Stores respondent demographic data used for survey eligibility."""

    # The seven details that make up the completion percentage, each counted equally.
    COMPLETION_FIELDS = (
        "age",
        "gender",
        "region",
        "interests",
        "education",
        "occupation",
        "marital_status",
    )

    profile_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="respondent_profile",
    )
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=16, choices=Gender.choices)
    # The field keeps the name "region"; its values are Governorate codes.
    # blank=True only for old rows the data migration could not map.
    region = models.CharField(max_length=32, choices=Governorate.choices, blank=True)
    interests = ArrayField(
        models.CharField(max_length=32, choices=Interest.choices),
        default=list,
        blank=True,
    )
    education = models.CharField(
        max_length=32, choices=Education.choices, blank=True, default=""
    )
    occupation = models.CharField(
        max_length=32, choices=Occupation.choices, blank=True, default=""
    )
    marital_status = models.CharField(
        max_length=32, choices=MaritalStatus.choices, blank=True, default=""
    )
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

    def update_profile(
        self,
        age,
        gender,
        region,
        interests,
        education=None,
        occupation=None,
        marital_status=None,
    ):
        """Update demographic values; an optional value of None keeps the stored one."""
        self.age = age
        self.gender = gender
        self.region = region
        self.interests = list(interests)
        if education is not None:
            self.education = education
        if occupation is not None:
            self.occupation = occupation
        if marital_status is not None:
            self.marital_status = marital_status

    def is_complete(self):
        """Return whether the four details required for targeting are present."""
        return bool(
            self.age
            and self.gender
            and self.region in Governorate.values
            and self.interests
        )

    def completion_percent(self):
        """Return the share of the seven profile details that are filled, in percent."""
        filled = sum(1 for name in self.COMPLETION_FIELDS if getattr(self, name))
        return round(filled * 100 / len(self.COMPLETION_FIELDS))
