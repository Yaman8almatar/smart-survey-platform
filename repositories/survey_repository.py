from django.db.models import Count

from apps.core.models import Survey
from core.enums import SurveyStatus


class SurveyRepository:
    """Provides database access for surveys and survey report metrics."""

    def save(self, survey):
        """Persist a survey."""
        survey.save()
        return survey

    def find_by_id(self, survey_id):
        """Return a survey by its primary key."""
        return Survey.objects.filter(survey_id=survey_id).first()

    def find_by_provider_id(self, provider_id):
        """Return surveys owned by the selected service provider."""
        return Survey.objects.filter(provider_id=provider_id)

    def find_published(self):
        """Return surveys currently available for respondent eligibility checks."""
        return Survey.objects.filter(status=SurveyStatus.PUBLISHED)

    def update(self, survey):
        """Persist changes to a survey."""
        survey.save()
        return survey

    def delete(self, survey_id):
        """Delete a survey by primary key."""
        return Survey.objects.filter(survey_id=survey_id).delete()

    def count_by_status(self):
        """Return survey counts grouped by publication status."""
        return (
            Survey.objects.values("status")
            .annotate(count=Count("survey_id"))
            .order_by("status")
        )

    def find_most_active(self, limit=5):
        """Return surveys ranked by submitted response count."""
        return (
            Survey.objects.annotate(response_count=Count("responses"))
            .filter(response_count__gt=0)
            .order_by("-response_count", "survey_id")[:limit]
        )
