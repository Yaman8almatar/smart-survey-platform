"""The owner check of the analytics services (AnalysisService and QualityService).

One function, so both services refuse with the same errors. QuestionService, SurveyService
and TargetingService keep their own checks, which carry other messages.
"""

from core.enums import UserType
from core.exceptions import SurveyNotFound, UnauthorizedAction


def ensure_survey_owner(survey_repository, provider_user, survey_id):
    """Return the survey when the provider owns it; one query, through the given repository."""
    if provider_user.user_type != UserType.SERVICE_PROVIDER:
        raise UnauthorizedAction("Only service providers can view survey analytics.")

    survey = survey_repository.find_by_id(survey_id)
    if survey is None:
        raise SurveyNotFound("Survey not found.")

    if survey.provider_id != provider_user.user_id:
        raise UnauthorizedAction("Only the survey owner can view survey analytics.")
    return survey
