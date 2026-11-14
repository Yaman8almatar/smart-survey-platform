from apps.core.models import ResponseDraft


class DraftRepository:
    """Provides database access for response drafts."""

    def find(self, survey_id, respondent_id):
        """Return the respondent's draft for a survey if one exists."""
        return ResponseDraft.objects.filter(
            survey_id=survey_id,
            respondent_id=respondent_id,
        ).first()

    def save(self, draft):
        """Persist a response draft."""
        draft.save()
        return draft

    def delete(self, survey_id, respondent_id):
        """Delete the respondent's draft for a survey; no error when there is none."""
        ResponseDraft.objects.filter(
            survey_id=survey_id,
            respondent_id=respondent_id,
        ).delete()
