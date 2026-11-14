from apps.core.models import Survey
from core.enums import QuestionType, SurveyStatus, UserType
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    TargetingCriteriaNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.targeting_service import TargetingService


class SurveyService:
    """Handles Survey management workflows and eligibility decisions."""

    MIN_CHOICE_OPTIONS = 2

    def __init__(
        self,
        survey_repository=None,
        question_repository=None,
        targeting_repository=None,
        response_repository=None,
        profile_repository=None,
        targeting_service=None,
    ):
        """Wire repositories and services used by survey workflows and eligibility checks."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.targeting_repository = targeting_repository or TargetingRepository()
        self.response_repository = response_repository or ResponseRepository()
        self.profile_repository = profile_repository or ProfileRepository()
        self.targeting_service = targeting_service or TargetingService()

    def create_survey(self, provider_user, title, description):
        """Create a draft survey for a service provider."""
        self._ensure_service_provider(provider_user)
        self._validate_survey_data(title)

        survey = Survey(
            provider=provider_user,
            title=title.strip(),
            description=description,
        )
        return self.survey_repository.save(survey)

    def update_survey(self, provider_user, survey_id, title, description):
        """Update the title and description of an owned draft survey."""
        survey = self._get_owned_survey(provider_user, survey_id)
        self._validate_survey_data(title)

        if not survey.can_edit():
            raise NotEditable("Only draft surveys can be updated.")

        survey.title = title.strip()
        survey.description = description
        return self.survey_repository.update(survey)

    def _validate_survey_data(self, title):
        """Validate required survey fields."""
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Survey title must be a non-empty string.")

    def delete_survey(self, provider_user, survey_id):
        """Delete an owned draft or closed survey."""
        survey = self._get_owned_survey(provider_user, survey_id)

        if not survey.can_delete():
            raise NotEditable("Only draft or closed surveys can be deleted.")

        return self.survey_repository.delete(survey.survey_id)

    def publish_survey(self, provider_user, survey_id):
        """Publish a complete draft survey after validating questions and targeting criteria."""
        survey = self._get_owned_survey(provider_user, survey_id)

        # Validate the status transition before changing the survey state.
        if not survey.can_edit():
            raise NotEditable("Only draft surveys can be published.")

        # Published surveys must have at least one question.
        questions = self.question_repository.find_by_survey_id(survey.survey_id)
        if not questions.exists():
            raise ValidationError("A survey must have at least one question.")

        # Every multiple-choice question must offer a real choice to be answerable.
        for question in questions:
            if (
                question.question_type == QuestionType.MULTIPLE_CHOICE
                and self.question_repository.find_options_by_question_id(
                    question.question_id
                ).count()
                < self.MIN_CHOICE_OPTIONS
            ):
                raise ValidationError(
                    "Multiple-choice questions need at least two options before publishing."
                )

        if self.targeting_repository.find_by_survey_id(survey.survey_id) is None:
            raise TargetingCriteriaNotFound("Survey targeting criteria is required.")

        survey.publish()
        return self.survey_repository.update(survey)

    def close_survey(self, provider_user, survey_id):
        """Close a published survey and prevent future respondent submissions."""
        survey = self._get_owned_survey(provider_user, survey_id)

        # Only published surveys can move to CLOSED.
        if survey.status != SurveyStatus.PUBLISHED:
            raise NotEditable("Only published surveys can be closed.")

        survey.close()
        return self.survey_repository.update(survey)

    def list_provider_surveys(self, provider_user):
        """List surveys owned by a service provider."""
        self._ensure_service_provider(provider_user)
        return self.survey_repository.find_by_provider_id(provider_user.user_id)

    def get_provider_survey(self, provider_user, survey_id):
        """Validate provider ownership before allowing access to survey analytics."""
        return self._get_owned_survey(provider_user, survey_id)

    def list_provider_survey_items(self, provider_user):
        """Return provider surveys with allowed action flags based on survey status."""
        self._ensure_service_provider(provider_user)
        return [
            {
                "survey": survey,
                **self._survey_action_flags(survey),
            }
            for survey in self.survey_repository.find_by_provider_id(provider_user.user_id)
        ]

    def get_eligible_surveys(self, respondent_user):
        """Return published unanswered surveys matching a respondent profile."""
        self._ensure_respondent(respondent_user)

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None or not profile.is_complete():
            return []

        return list(
            self.survey_repository.find_eligible_for_respondent(
                profile=profile,
                respondent_user_id=respondent_user.user_id,
            )
        )

    def get_eligible_survey_items(self, respondent_user):
        """Return eligible surveys with their question counts."""
        self._ensure_respondent(respondent_user)

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None or not profile.is_complete():
            return []

        surveys = self.survey_repository.find_eligible_for_respondent(
            profile=profile,
            respondent_user_id=respondent_user.user_id,
        )

        return [
            {
                "survey": survey,
                "question_count": getattr(survey, "question_count", 0),
            }
            for survey in surveys
        ]

    def _get_owned_survey(self, provider_user, survey_id):
        """Return a survey after validating provider ownership."""
        self._ensure_service_provider(provider_user)

        survey = self.survey_repository.find_by_id(survey_id)
        if survey is None:
            raise SurveyNotFound("Survey not found.")

        if survey.provider_id != provider_user.user_id:
            raise UnauthorizedAction("Only the survey owner can perform this action.")

        return survey

    def _ensure_service_provider(self, user):
        """Ensure only service providers can manage surveys."""
        if user.user_type != UserType.SERVICE_PROVIDER:
            raise UnauthorizedAction("Only service providers can manage surveys.")

    def _ensure_respondent(self, user):
        """Ensure only respondents can browse eligible surveys."""
        if user.user_type != UserType.RESPONDENT:
            raise UnauthorizedAction("Only respondents can view eligible surveys.")

    def _survey_action_flags(self, survey):
        """Build provider action flags for a survey based on its status."""
        # Build Survey status action flags for provider pages.
        is_draft = survey.status == SurveyStatus.DRAFT
        is_published = survey.status == SurveyStatus.PUBLISHED
        is_closed = survey.status == SurveyStatus.CLOSED

        return {
            "can_edit": is_draft,
            "can_delete": survey.can_delete(),
            "can_publish": is_draft,
            "can_close": is_published,
            "can_manage_questions": is_draft,
            "can_manage_targeting": is_draft,
            "can_view_analytics": is_published or is_closed,
        }
