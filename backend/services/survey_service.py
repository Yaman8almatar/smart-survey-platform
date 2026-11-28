import secrets

from django.conf import settings
from django.utils import timezone

from apps.core.models import Survey
from core.enums import QuestionType, SurveyStatus, UserType
from core.exceptions import (
    InvitationNotFound,
    NotEditable,
    SurveyNotFound,
    TargetingCriteriaNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.quality_repository import QualityRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.expected_time import expected_minutes
from services.targeting_service import TargetingService


class SurveyService:
    """Handles Survey management workflows and eligibility decisions."""

    MIN_CHOICE_OPTIONS = 2
    # FR-11: results open at 5 responses, so a smaller limit would never show any.
    MIN_TARGET_RESPONSES = 5
    MAX_TARGET_RESPONSES = 10000
    # FR-10: states in which a survey has an invitation link.
    SHAREABLE_STATUSES = frozenset(
        {SurveyStatus.PUBLISHED, SurveyStatus.PAUSED, SurveyStatus.CLOSED}
    )

    def __init__(
        self,
        survey_repository=None,
        question_repository=None,
        targeting_repository=None,
        response_repository=None,
        profile_repository=None,
        targeting_service=None,
        quality_repository=None,
    ):
        """Wire repositories and services used by survey workflows and eligibility checks."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.targeting_repository = targeting_repository or TargetingRepository()
        self.response_repository = response_repository or ResponseRepository()
        self.profile_repository = profile_repository or ProfileRepository()
        self.targeting_service = targeting_service or TargetingService()
        self.quality_repository = quality_repository or QualityRepository()

    def create_survey(
        self,
        provider_user,
        title,
        description,
        shuffle_questions=False,
        shuffle_options=False,
        opens_on=None,
        closes_on=None,
        target_responses=None,
    ):
        """Create a draft survey for a service provider."""
        self._ensure_service_provider(provider_user)
        self._validate_survey_data(
            title, shuffle_questions, shuffle_options, opens_on, closes_on, target_responses
        )

        survey = Survey(
            provider=provider_user,
            title=title.strip(),
            description=description,
            shuffle_questions=shuffle_questions,
            shuffle_options=shuffle_options,
            opens_on=opens_on,
            closes_on=closes_on,
            target_responses=target_responses,
        )
        return self.survey_repository.save(survey)

    def update_survey(
        self,
        provider_user,
        survey_id,
        title,
        description,
        shuffle_questions=False,
        shuffle_options=False,
        opens_on=None,
        closes_on=None,
        target_responses=None,
    ):
        """Update the title, description, order, schedule and limit of an owned draft survey."""
        survey = self._get_owned_survey(provider_user, survey_id)
        self._validate_survey_data(
            title, shuffle_questions, shuffle_options, opens_on, closes_on, target_responses
        )

        # FR-16: a published survey's order settings never change, like the rest of it.
        if not survey.can_edit():
            raise NotEditable("Only draft surveys can be updated.")

        survey.title = title.strip()
        survey.description = description
        survey.shuffle_questions = shuffle_questions
        survey.shuffle_options = shuffle_options
        survey.opens_on = opens_on
        survey.closes_on = closes_on
        survey.target_responses = target_responses
        return self.survey_repository.update(survey)

    def _validate_survey_data(
        self,
        title,
        shuffle_questions=False,
        shuffle_options=False,
        opens_on=None,
        closes_on=None,
        target_responses=None,
    ):
        """Validate required survey fields, the FR-16 order settings and the FR-11 settings."""
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Survey title must be a non-empty string.")
        if not isinstance(shuffle_questions, bool) or not isinstance(shuffle_options, bool):
            raise ValidationError("Shuffle settings must be true or false.")
        self._validate_schedule(opens_on, closes_on)
        if target_responses is not None:
            if (
                isinstance(target_responses, bool)
                or not isinstance(target_responses, int)
                or target_responses < self.MIN_TARGET_RESPONSES
            ):
                raise ValidationError("The response limit must be at least 5.")
            if target_responses > self.MAX_TARGET_RESPONSES:
                raise ValidationError("The response limit must be 10,000 or fewer.")

    def _validate_schedule(self, opens_on, closes_on):
        """Validate the FR-11 dates; an empty date means no bound."""
        if opens_on is not None and closes_on is not None and opens_on > closes_on:
            raise ValidationError("The opening date must be on or before the closing date.")
        if closes_on is not None and closes_on < timezone.localdate():
            raise ValidationError("The closing date cannot be in the past.")

    def delete_survey(self, provider_user, survey_id):
        """Delete an owned draft or closed survey."""
        survey = self._get_owned_survey(provider_user, survey_id)

        if not survey.can_delete():
            raise NotEditable("Only draft or closed surveys can be deleted.")

        # P-06: responses are evidence; a survey that has them is kept (A-219).
        if self.response_repository.survey_has_responses(survey.survey_id):
            raise NotEditable("A survey that has responses cannot be deleted.")

        return self.survey_repository.delete(survey.survey_id)

    def submit_for_review(self, provider_user, survey_id):
        """Submit a complete draft survey for admin review (FR-12); it is locked until then."""
        survey, _, _ = self._get_publishable_survey(provider_user, survey_id)

        # The reach is counted at approval, when the survey is published.
        survey.submit_for_review()
        return self.survey_repository.update(survey)

    def get_publish_preview(self, provider_user, survey_id):
        """Return what the publish confirmation shows; raises what publishing would raise."""
        _, question_count, criteria = self._get_publishable_survey(provider_user, survey_id)
        return {
            "reach": self.targeting_service.describe_reach(criteria),
            "criteria": self.targeting_service.criteria_values(criteria),
            "question_count": question_count,
        }

    def _get_publishable_survey(self, provider_user, survey_id):
        """Run every publish check; return the survey, its question count and its criteria."""
        survey = self._get_owned_survey(provider_user, survey_id)

        # Validate the status transition before changing the survey state.
        if not survey.can_edit():
            raise NotEditable("Only draft surveys can be submitted for review.")

        # FR-11: a closing date may have passed since the draft was saved.
        self._validate_schedule(survey.opens_on, survey.closes_on)

        # Published surveys must have at least one question.
        questions = list(self.question_repository.find_by_survey_id(survey.survey_id))
        if not questions:
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
            # The expected option may have been deleted since (SET_NULL).
            if question.is_attention_check and (
                question.expected_option_id is None and question.expected_rating is None
            ):
                raise ValidationError("An attention check needs its expected answer.")

        criteria = self.targeting_repository.find_by_survey_id(survey.survey_id)
        if criteria is None:
            raise TargetingCriteriaNotFound("Survey targeting criteria is required.")

        return survey, len(questions), criteria

    def close_survey(self, provider_user, survey_id):
        """Close a published or paused survey and prevent future respondent submissions."""
        survey = self._get_owned_survey(provider_user, survey_id)

        # Only published or paused surveys can move to CLOSED.
        if survey.status not in {SurveyStatus.PUBLISHED, SurveyStatus.PAUSED}:
            raise NotEditable("Only published or paused surveys can be closed.")

        survey.close()
        return self.survey_repository.update(survey)

    def pause_survey(self, provider_user, survey_id):
        """Stop a published survey from taking responses until it is resumed (FR-11)."""
        survey = self._get_owned_survey(provider_user, survey_id)
        if survey.status != SurveyStatus.PUBLISHED:
            raise NotEditable("Only published surveys can be paused.")
        survey.pause()
        return self.survey_repository.update(survey)

    def resume_survey(self, provider_user, survey_id):
        """Let a paused survey take responses again (FR-11)."""
        survey = self._get_owned_survey(provider_user, survey_id)
        if survey.status != SurveyStatus.PAUSED:
            raise NotEditable("Only paused surveys can be resumed.")
        survey.resume()
        return self.survey_repository.update(survey)

    def get_invitation(self, provider_user, survey_id):
        """Return the owned survey and its stable invitation link (FR-10).

        The token is made the first time the link is asked for, and only for a survey that
        is published, paused or closed.
        """
        survey = self._get_owned_survey(provider_user, survey_id)
        if survey.status not in self.SHAREABLE_STATUSES:
            raise NotEditable("The invitation link is available once the survey is published.")

        if not survey.invite_token:
            survey.invite_token = self.survey_repository.set_invite_token_if_empty(
                survey.survey_id, secrets.token_urlsafe(16)
            )
        return {
            "survey": survey,
            "link": f"{settings.APP_PUBLIC_URL}/?invite={survey.invite_token}",
        }

    def resolve_invitation(self, respondent_user, token):
        """Turn an invitation token into a survey id (FR-10).

        Checks only that the token names a shareable survey; every rule about who may answer
        stays in ResponseService.ensure_can_answer.
        """
        self._ensure_respondent(respondent_user)

        survey = self.survey_repository.find_by_invite_token(token)
        if survey is None or survey.status not in self.SHAREABLE_STATUSES:
            raise InvitationNotFound("This invitation link is not valid.")

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        return {
            "survey_id": survey.survey_id,
            "profile_complete": profile is not None and profile.is_complete(),
        }

    def list_provider_surveys(self, provider_user):
        """List surveys owned by a service provider."""
        self._ensure_service_provider(provider_user)
        # FR-11: a survey past its closing date is closed when it is next read.
        self.survey_repository.close_past_end(timezone.localdate())
        return self.survey_repository.find_by_provider_id(provider_user.user_id)

    def get_provider_survey(self, provider_user, survey_id):
        """Validate provider ownership before allowing access to survey analytics."""
        return self._get_owned_survey(provider_user, survey_id)

    def list_provider_survey_items(self, provider_user):
        """Return provider surveys with allowed action flags based on survey status."""
        self._ensure_service_provider(provider_user)
        self.survey_repository.close_past_end(timezone.localdate())
        return [
            {
                "survey": survey,
                **self._survey_action_flags(survey),
            }
            for survey in self.survey_repository.find_by_provider_id(provider_user.user_id)
        ]

    def get_eligible_survey_items(self, respondent_user):
        """Return eligible surveys, most shared interests first, with counts, minutes and date."""
        self._ensure_respondent(respondent_user)

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None or not profile.is_complete():
            return []

        surveys = list(
            self.survey_repository.find_eligible_for_respondent(
                profile=profile,
                respondent_user_id=respondent_user.user_id,
            )
        )
        valid_active_ms = self.quality_repository.find_valid_active_ms_by_survey_ids(
            [survey.survey_id for survey in surveys]
        )

        # FR-08: most shared interests first; sorted() is stable, so equal counts keep the
        # repository's order (newest published first).
        interests = set(profile.interests)
        surveys = sorted(
            surveys,
            key=lambda survey: -len(interests.intersection(survey.criteria.interests)),
        )

        return [
            {
                "survey": survey,
                "question_count": getattr(survey, "question_count", 0),
                "expected_minutes": expected_minutes(
                    {
                        QuestionType.MULTIPLE_CHOICE.value: survey.choice_count,
                        QuestionType.RATING_SCALE.value: survey.rating_count,
                        QuestionType.OPEN_TEXT.value: survey.open_count,
                    },
                    valid_active_ms.get(survey.survey_id, []),
                ),
                "published_on": self._published_on(survey),
                "closes_on": survey.closes_on,
            }
            for survey in surveys
        ]

    def _published_on(self, survey):
        """Return the later of the publish day and the opening date (FR-11); either may be empty."""
        days = [survey.opens_on]
        if survey.published_at:
            days.append(timezone.localdate(survey.published_at))
        days = [day for day in days if day is not None]
        return max(days) if days else None

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
        is_paused = survey.status == SurveyStatus.PAUSED
        is_closed = survey.status == SurveyStatus.CLOSED

        return {
            "can_edit": is_draft,
            "can_delete": survey.can_delete(),
            "can_submit": is_draft,
            "is_pending_review": survey.is_pending_review(),
            "can_close": is_published or is_paused,
            "can_pause": is_published,
            "can_resume": is_paused,
            "can_manage_questions": is_draft,
            "can_manage_targeting": is_draft,
            "can_view_analytics": is_published or is_paused or is_closed,
            "can_share": survey.status in self.SHAREABLE_STATUSES,
        }
