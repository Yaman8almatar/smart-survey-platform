from django.db import models

from core.enums import Gender


class TargetingCriteria(models.Model):
    """Stores optional demographic restrictions for a survey audience."""

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
    region = models.CharField(max_length=255, null=True, blank=True)

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
            and not self.region
        )
