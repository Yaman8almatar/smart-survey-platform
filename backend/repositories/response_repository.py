from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.core.models import Answer, Response
from repositories.date_ranges import aware_day_range

# FR-09: a response's number is its position in this order; "Response 1" came first.
RESPONSE_NUMBER_ORDER = ("submitted_at", "response_id")


class ResponseRepository:
    """Provides database access for responses, answers, and response metrics."""

    def save(self, response):
        """Persist a survey response."""
        response.save()
        return response

    def find_by_survey_and_respondent(self, survey_id, respondent_id):
        """Return a respondent response for a survey if one exists."""
        return Response.objects.filter(
            survey_id=survey_id,
            respondent_id=respondent_id,
        ).first()

    def find_by_survey_id(self, survey_id):
        """Return responses linked to the selected survey."""
        return Response.objects.filter(survey_id=survey_id)

    def count_submitted_for_survey(self, survey_id):
        """Return how many responses were submitted for a survey, excluded ones too (P-08)."""
        return Response.objects.filter(survey_id=survey_id).count()

    def count_included_by_survey_id(self, survey_id):
        """Return how many responses of a survey the provider has not excluded."""
        return Response.objects.filter(survey_id=survey_id, is_excluded=False).count()

    def find_excluded_ids_by_survey_id(self, survey_id):
        """Return the ids of the excluded responses of a survey."""
        return list(
            Response.objects.filter(survey_id=survey_id, is_excluded=True)
            .order_by("response_id")
            .values_list("response_id", flat=True)
        )

    def find_by_number(self, survey_id, number):
        """Return {"response_id", "has_evidence"} of the response at a number, in one query.

        The number counts from 1 in RESPONSE_NUMBER_ORDER; None when no response has it.
        """
        if number < 1:
            return None
        rows = list(
            Response.objects.filter(survey_id=survey_id)
            .order_by(*RESPONSE_NUMBER_ORDER)
            .values("response_id", "quality__quality_id")[number - 1 : number]
        )
        row = rows[0] if rows else None
        if row is None:
            return None
        return {
            "response_id": row["response_id"],
            "has_evidence": row["quality__quality_id"] is not None,
        }

    def lock_exclusion_states(self, survey_id, response_ids):
        """Lock the given responses of a survey and return {response_id: is_excluded}.

        Ids that do not belong to the survey are absent. Call inside a transaction.
        """
        return dict(
            Response.objects.select_for_update()
            .filter(survey_id=survey_id, response_id__in=response_ids)
            .order_by("response_id")
            .values_list("response_id", "is_excluded")
        )

    def set_excluded(self, response_ids, excluded, excluded_at):
        """Set is_excluded and excluded_at of the given responses in one update."""
        return Response.objects.filter(response_id__in=response_ids).update(
            is_excluded=excluded,
            excluded_at=excluded_at,
        )

    def find_by_respondent_id(self, respondent_id):
        """Return responses previously submitted by the selected respondent."""
        return (
            Response.objects.filter(respondent_id=respondent_id)
            .select_related("survey")
            .order_by("-submitted_at")
        )

    def has_response_for_survey(self, survey_id, respondent_id):
        """Return whether a respondent already answered a survey."""
        return Response.objects.filter(
            survey_id=survey_id,
            respondent_id=respondent_id,
        ).exists()

    def survey_has_responses(self, survey_id):
        """Return whether any response was submitted for a survey."""
        return Response.objects.filter(survey_id=survey_id).exists()

    def save_answer(self, answer):
        """Persist a response answer."""
        answer.save()
        return answer

    def find_answers_by_response_id(self, response_id):
        """Return answers belonging to one response."""
        return Answer.objects.filter(response_id=response_id)

    def find_answers_with_options_by_response_id(self, response_id):
        """Return the answers of one response with their selected option, in one query."""
        return list(
            Answer.objects.filter(response_id=response_id).select_related("selected_option")
        )

    def find_answers_by_survey_id(self, survey_id):
        """Return answers submitted for a survey."""
        return Answer.objects.filter(
            response__survey_id=survey_id,
        ).select_related("question", "selected_option")

    def find_included_answers_by_survey_id(self, survey_id):
        """Return the answers of a survey's responses that the provider has not excluded."""
        return self.find_answers_by_survey_id(survey_id).filter(response__is_excluded=False)

    def count_submitted_by_date(self, date_from, date_to):
        """Return response counts grouped by submission date."""
        start_dt, end_dt = aware_day_range(date_from, date_to)
        return (
            Response.objects.filter(
                submitted_at__range=(start_dt, end_dt),
            )
            .annotate(submitted_date=TruncDate("submitted_at"))
            .values("submitted_date")
            .annotate(count=Count("response_id"))
            .order_by("submitted_date")
        )

    def total_responses(self):
        """Return total number of submitted responses across all surveys."""
        return Response.objects.count()

    def count_by_survey(self):
        """Return response counts grouped by survey."""
        return (
            Response.objects.values("survey_id")
            .annotate(response_count=Count("response_id"))
            .order_by("-response_count", "survey_id")
        )
