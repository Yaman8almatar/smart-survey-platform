from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.core.models import Answer, Response


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

    def save_answer(self, answer):
        """Persist a response answer."""
        answer.save()
        return answer

    def find_answers_by_response_id(self, response_id):
        """Return answers belonging to one response."""
        return Answer.objects.filter(response_id=response_id)

    def find_answers_by_survey_id(self, survey_id):
        """Return answers submitted for a survey."""
        return Answer.objects.filter(
            response__survey_id=survey_id,
        ).select_related("question", "selected_option")

    def count_submitted_by_date(self, date_from, date_to):
        """Return response counts grouped by submission date."""
        return (
            Response.objects.filter(
                submitted_at__date__gte=date_from,
                submitted_at__date__lte=date_to,
            )
            .annotate(submitted_date=TruncDate("submitted_at"))
            .values("submitted_date")
            .annotate(count=Count("response_id"))
            .order_by("submitted_date")
        )

    def count_by_survey(self):
        """Return response counts grouped by survey."""
        return (
            Response.objects.values("survey_id")
            .annotate(response_count=Count("response_id"))
            .order_by("-response_count", "survey_id")
        )
