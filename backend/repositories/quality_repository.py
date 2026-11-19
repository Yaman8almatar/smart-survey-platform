from apps.core.models import Answer, Response, ResponseQuality

# The response and evidence columns the quality rules read; no profile snapshot column.
EVIDENCE_FIELDS = (
    "response_id",
    "respondent_id",
    "submitted_at",
    "is_excluded",
    "quality__quality_id",
    "quality__timings",
    "quality__active_ms",
    "quality__attention_total",
    "quality__attention_failed",
    "quality__rating_count",
    "quality__rating_all_same",
    "quality__device_hash",
    "quality__signals_ok",
)


class QualityRepository:
    """Provides database access for the FR-04 evidence of responses."""

    def save(self, quality):
        """Persist the evidence row of one response."""
        quality.save()
        return quality

    def find_evidence_by_survey_id(self, survey_id):
        """Return one dictionary per submitted response of a survey with its evidence, in one query.

        A response without an evidence row (collected before FR-04) has quality__quality_id None.
        """
        return list(
            Response.objects.filter(survey_id=survey_id)
            .order_by("response_id")
            .values(*EVIDENCE_FIELDS)
        )

    def find_answered_questions_by_survey_id(self, survey_id):
        """Return (response_id, question_id, question_type) of every answer of a survey, in one query."""
        return list(
            Answer.objects.filter(response__survey_id=survey_id).values_list(
                "response_id", "question_id", "question__question_type"
            )
        )
