from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from apps.core.models import Response, Survey, TargetingCriteria
from core.enums import Gender, QuestionType, SurveyStatus


class SurveyRepository:
    """Provides database access for surveys and survey report metrics."""

    def save(self, survey):
        """Persist a survey."""
        survey.save()
        return survey

    def find_by_id(self, survey_id):
        """Return a survey by its primary key."""
        return Survey.objects.filter(survey_id=survey_id).first()

    def find_by_id_for_update(self, survey_id):
        """Return a survey with its row locked; call only inside transaction.atomic()."""
        return Survey.objects.select_for_update().filter(survey_id=survey_id).first()

    def find_pending_review(self):
        """Return surveys waiting for review, oldest submission first, with question counts."""
        return (
            Survey.objects.filter(status=SurveyStatus.PENDING_REVIEW)
            .select_related("provider")
            .annotate(question_count=Count("questions", distinct=True))
            .order_by("submitted_at", "survey_id")
        )

    def count_pending_review(self):
        """Return how many surveys are waiting for review."""
        return Survey.objects.filter(status=SurveyStatus.PENDING_REVIEW).count()

    def close_past_end(self, today):
        """Close every published or paused survey whose closing date is before today (FR-11).

        One UPDATE; returns how many surveys it closed.
        """
        return Survey.objects.filter(
            status__in=[SurveyStatus.PUBLISHED, SurveyStatus.PAUSED],
            closes_on__lt=today,
        ).update(status=SurveyStatus.CLOSED, closed_at=timezone.now())

    def find_by_provider_id(self, provider_id):
        """Return surveys owned by the selected service provider."""
        return Survey.objects.filter(provider_id=provider_id)

    def find_eligible_for_respondent(self, profile, respondent_user_id):
        """Return published unanswered surveys matching respondent demographics with question counts.

        Each survey carries question_count and the count of each type: choice_count,
        rating_count and open_count.
        """
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
        # P-17, query form; TargetingService.profile_matches_criteria is the Python form and
        # the parity test keeps both equal (P-18). An empty list means no restriction.
        list_filters = [
            Q(**{f"criteria__{list_name}": []})
            | Q(**{f"criteria__{list_name}__contains": [getattr(profile, profile_field)]})
            for list_name, profile_field in TargetingCriteria.SINGLE_VALUE_LISTS
        ]
        interests_filter = (
            Q(criteria__interests=[])
            | Q(criteria__interests__overlap=list(profile.interests))
        )
        # FR-11: open now, by the schedule; an empty date means no bound.
        today = timezone.localdate()
        opened_filter = Q(opens_on__isnull=True) | Q(opens_on__lte=today)
        not_past_closing_filter = Q(closes_on__isnull=True) | Q(closes_on__gte=today)

        return (
            Survey.objects.filter(
                status=SurveyStatus.PUBLISHED,
                criteria__isnull=False,
            )
            .filter(
                gender_filter,
                age_min_filter,
                age_max_filter,
                *list_filters,
                interests_filter,
                opened_filter,
                not_past_closing_filter,
            )
            .filter(~Exists(has_responded))
            .annotate(
                question_count=Count("questions", distinct=True),
                # FR-08: the expected-time estimate reads the count of each question type.
                choice_count=Count(
                    "questions",
                    filter=Q(questions__question_type=QuestionType.MULTIPLE_CHOICE),
                    distinct=True,
                ),
                rating_count=Count(
                    "questions",
                    filter=Q(questions__question_type=QuestionType.RATING_SCALE),
                    distinct=True,
                ),
                open_count=Count(
                    "questions",
                    filter=Q(questions__question_type=QuestionType.OPEN_TEXT),
                    distinct=True,
                ),
            )
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
