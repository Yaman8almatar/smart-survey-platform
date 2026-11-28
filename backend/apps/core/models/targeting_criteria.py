from django.contrib.postgres.fields import ArrayField
from django.db import models

from core.enums import (
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
)


class TargetingCriteria(models.Model):
    """Stores optional demographic restrictions for a survey audience."""

    # Each list here restricts one single-value profile detail (P-17); interests are an
    # overlap of two lists and are matched apart.
    SINGLE_VALUE_LISTS = (
        ("regions", "region"),
        ("education_levels", "education"),
        ("occupations", "occupation"),
        ("marital_statuses", "marital_status"),
    )

    criteria_id = models.BigAutoField(primary_key=True)
    survey = models.OneToOneField(
        "core.Survey",
        on_delete=models.CASCADE,
        related_name="criteria",
    )
    gender = models.CharField(
        max_length=16,
        choices=Gender.choices,
        null=True,
        blank=True,
    )
    age_min = models.PositiveIntegerField(null=True, blank=True)
    age_max = models.PositiveIntegerField(null=True, blank=True)
    # FR-03 (P-17): each list is one restriction; an empty list means no restriction.
    regions = ArrayField(
        models.CharField(max_length=32, choices=Governorate.choices),
        default=list,
        blank=True,
    )
    education_levels = ArrayField(
        models.CharField(max_length=32, choices=Education.choices),
        default=list,
        blank=True,
    )
    occupations = ArrayField(
        models.CharField(max_length=32, choices=Occupation.choices),
        default=list,
        blank=True,
    )
    marital_statuses = ArrayField(
        models.CharField(max_length=32, choices=MaritalStatus.choices),
        default=list,
        blank=True,
    )
    interests = ArrayField(
        models.CharField(max_length=32, choices=Interest.choices),
        default=list,
        blank=True,
    )

    class Meta:
        db_table = "survey_targeting_criteria"

    def __str__(self):
        """Return a readable targeting criteria label."""
        return f"Targeting criteria for {self.survey}"

    def is_open_to_all(self):
        """Return whether the criteria has no demographic restrictions."""
        return (
            self.gender in [None, "", Gender.ANY]
            and self.age_min is None
            and self.age_max is None
            and not self.regions
            and not self.education_levels
            and not self.occupations
            and not self.marital_statuses
            and not self.interests
        )
