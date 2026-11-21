from django.db import transaction
from django.utils import timezone

from core.enums import UserType
from core.exceptions import NotEditable, SurveyNotFound, UnauthorizedAction, ValidationError
from repositories.profile_repository import ProfileRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.question_service import QuestionService
from services.targeting_service import TargetingService


class SurveyReviewService:
    """Handles the admin review of submitted surveys (FR-12): approve or reject with a reason."""

    MAX_REASON_LENGTH = 1000

    def __init__(
        self,
        survey_repository=None,
        targeting_repository=None,
        profile_repository=None,
        targeting_service=None,
        question_service=None,
    ):
        """Wire repositories and services used by the review workflows."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.targeting_repository = targeting_repository or TargetingRepository()
        self.profile_repository = profile_repository or ProfileRepository()
        self.targeting_service = targeting_service or TargetingService()
        self.question_service = question_service or QuestionService()

    def count_pending(self, admin_user):
        """Return how many surveys are waiting for review."""
        self._ensure_admin(admin_user)
        return self.survey_repository.count_pending_review()

    def list_pending(self, admin_user):
        """Return the surveys waiting for review, oldest submission first."""
        self._ensure_admin(admin_user)
        return [
            {
                "survey": survey,
                "provider_name": survey.provider.name,
                "provider_email": survey.provider.email,
                "submitted_at": survey.submitted_at,
                "question_count": survey.question_count,
            }
            for survey in self.survey_repository.find_pending_review()
        ]

    def get_review(self, admin_user, survey_id):
        """Return what the admin reads before deciding: the survey, its targeting and questions."""
        self._ensure_admin(admin_user)
        survey = self._ensure_pending(self.survey_repository.find_by_id(survey_id))
        criteria = self.targeting_repository.find_by_survey_id(survey.survey_id)
        return {
            "survey": survey,
            "provider_name": survey.provider.name,
            "provider_email": survey.provider.email,
            "submitted_at": survey.submitted_at,
            "reach": self.targeting_service.describe_reach(criteria),
            "criteria": self.targeting_service.criteria_values(criteria),
            "questions": self.question_service.get_review_question_rows(
                admin_user, survey.survey_id
            ),
        }

    def approve(self, admin_user, survey_id):
        """Publish a pending survey and store its reach at that moment."""
        self._ensure_admin(admin_user)
        with transaction.atomic():
            # The lock keeps two admins from deciding on the same survey at once.
            survey = self._ensure_pending(
                self.survey_repository.find_by_id_for_update(survey_id)
            )
            # FR-11: publishing a survey already past its closing date would close it at once.
            if survey.has_passed_closing(timezone.localdate()):
                raise ValidationError(
                    "The closing date has passed. Reject the survey so the provider can change it."
                )
            criteria = self.targeting_repository.find_by_survey_id(survey.survey_id)
            # Unbanded on purpose: every display of reach_at_publish goes through disclosure.band.
            survey.reach_at_publish = self.profile_repository.count_matching(criteria)
            survey.approve(admin_user)
            return self.survey_repository.update(survey)

    def reject(self, admin_user, survey_id, reason):
        """Return a pending survey to its provider as a draft with the admin's reason."""
        self._ensure_admin(admin_user)
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("Write a reason for the provider.")
        if len(reason) > self.MAX_REASON_LENGTH:
            raise ValidationError("The reason must be 1000 characters or fewer.")

        with transaction.atomic():
            survey = self._ensure_pending(
                self.survey_repository.find_by_id_for_update(survey_id)
            )
            survey.reject(admin_user, reason)
            return self.survey_repository.update(survey)

    def _ensure_admin(self, user):
        """Ensure only administrators can review surveys."""
        if user.user_type != UserType.ADMIN:
            raise UnauthorizedAction("Only admins can perform this action.")

    def _ensure_pending(self, survey):
        """Return the survey when it is still waiting for review."""
        if survey is None:
            raise SurveyNotFound("Survey not found.")
        if not survey.is_pending_review():
            raise NotEditable("This survey is no longer waiting for review.")
        return survey
