from apps.core.models import TargetingCriteria


class TargetingRepository:
    """Provides database access for survey Targeting criteria."""

    def save(self, criteria):
        """Persist targeting criteria."""
        criteria.save()
        return criteria

    def find_by_survey_id(self, survey_id):
        """Return targeting criteria for a survey."""
        return TargetingCriteria.objects.filter(survey_id=survey_id).first()

    def update(self, criteria):
        """Persist changes to targeting criteria."""
        criteria.save()
        return criteria

    def create_or_update(
        self,
        survey,
        gender=None,
        age_min=None,
        age_max=None,
        region=None,
    ):
        """Create or update the targeting criteria for a survey."""
        criteria, _created = TargetingCriteria.objects.update_or_create(
            survey=survey,
            defaults={
                "gender": gender,
                "age_min": age_min,
                "age_max": age_max,
                "region": region,
            },
        )
        return criteria
