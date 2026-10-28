from django.db.models import Count, Exists, OuterRef, Q
from django.db.models.functions import Lower, Trim

from apps.core.models import Response, Survey
from core.enums import Gender, SurveyStatus


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

    def find_eligible_for_respondent(self, profile, respondent_user_id):
        """Return published unanswered surveys matching respondent demographics with question counts."""
        has_responded = Response.objects.filter(
            survey=OuterRef("pk"),
            respondent_id=respondent_user_id,
        )

        gender_filter = (
            Q(criteria__gender__isnull=True)
            | Q(criteria__gender="")
            | Q(criteria__gender=Gender.ANY)
            | Q(criteria__gender=profile.gender)
        )
        age_min_filter = (
            Q(criteria__age_min__isnull=True)
            | Q(criteria__age_min__lte=profile.age)
        )
        age_max_filter = (
            Q(criteria__age_max__isnull=True)
            | Q(criteria__age_max__gte=profile.age)
        )
        region_clean_lower = (profile.region or "").strip().casefold()
        region_filter = (
            Q(criteria__region__isnull=True)
            | Q(clean_criteria_region="")
            | Q(clean_criteria_region=region_clean_lower)
        )

        return (
            Survey.objects.filter(
                status=SurveyStatus.PUBLISHED,
                criteria__isnull=False,
            )
            .annotate(clean_criteria_region=Lower(Trim("criteria__region")))
            .filter(
                gender_filter,
                age_min_filter,
                age_max_filter,
                region_filter,
            )
            .filter(~Exists(has_responded))
            .annotate(question_count=Count("questions", distinct=True))
            .select_related("criteria")
            .order_by("-published_at", "-survey_id")
        )

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
