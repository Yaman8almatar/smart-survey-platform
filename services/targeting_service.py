from core.enums import Gender, UserType
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository


class TargetingService:
    """Handles Targeting criteria persistence and respondent matching."""

    MAX_AGE = 120

    def __init__(
        self,
        survey_repository=None,
        targeting_repository=None,
        profile_repository=None,
    ):
        """Wire repositories used by targeting criteria workflows."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.targeting_repository = targeting_repository or TargetingRepository()
        self.profile_repository = profile_repository or ProfileRepository()

    def save_criteria(
        self,
        provider_user,
        survey_id,
        gender=None,
        age_min=None,
        age_max=None,
        region=None,
    ):
        """Create or update targeting criteria for an owned draft survey."""
        survey = self._get_owned_draft_survey(provider_user, survey_id)
        self._validate_criteria(gender, age_min, age_max, region)
        return self.targeting_repository.create_or_update(
            survey=survey,
            gender=gender,
            age_min=age_min,
            age_max=age_max,
            region=region,
        )

    def match_respondent_to_survey(self, respondent_user, survey_id):
        """Return whether a respondent profile matches survey targeting criteria."""
        if respondent_user.user_type != UserType.RESPONDENT:
            return False

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None or not profile.is_complete():
            return False

        criteria = self.targeting_repository.find_by_survey_id(survey_id)
        if criteria is None:
            return False

        return self._matches_profile(criteria, profile)

    def get_criteria_initial(self, provider_user, survey_id):
        """Return targeting criteria values for pre-filling the targeting form."""
        self._get_owned_survey(provider_user, survey_id)
        criteria = self.targeting_repository.find_by_survey_id(survey_id)

        if criteria is None:
            return {}

        return {
            "gender": criteria.gender or "",
            "age_min": criteria.age_min,
            "age_max": criteria.age_max,
            "region": criteria.region or "",
        }

    def _get_owned_draft_survey(self, provider_user, survey_id):
        """Return an owned draft survey for targeting edits."""
        survey = self._get_owned_survey(provider_user, survey_id)

        if not survey.can_edit():
            raise NotEditable("Targeting criteria can only be updated for draft surveys.")

        return survey

    def _get_owned_survey(self, provider_user, survey_id):
        """Return a survey after validating targeting ownership."""
        self._ensure_service_provider(provider_user)

        survey = self.survey_repository.find_by_id(survey_id)
        if survey is None:
            raise SurveyNotFound("Survey not found.")

        if survey.provider_id != provider_user.user_id:
            raise UnauthorizedAction("Only the survey owner can define targeting.")

        return survey

    def _ensure_service_provider(self, user):
        """Ensure only service providers can define targeting."""
        if user.user_type != UserType.SERVICE_PROVIDER:
            raise UnauthorizedAction("Only service providers can define targeting.")

    def _validate_criteria(self, gender, age_min, age_max, region):
        """Validate demographic targeting criteria before saving."""
        # Gender.ANY is valid here because it means no gender restriction.
        if gender not in {None, Gender.MALE, Gender.FEMALE, Gender.ANY}:
            raise ValidationError("Gender must be MALE, FEMALE, ANY, or None.")

        self._validate_age("age_min", age_min)
        self._validate_age("age_max", age_max)

        if age_min is not None and age_max is not None and age_min > age_max:
            raise ValidationError("Minimum age must be less than or equal to maximum age.")

        if region is not None and (not isinstance(region, str) or not region.strip()):
            raise ValidationError("Region must be None or a non-empty string.")

    def _validate_age(self, field_name, age):
        """Validate optional targeting age bounds."""
        if age is None:
            return

        if type(age) is not int or age < 0 or age > self.MAX_AGE:
            raise ValidationError(f"{field_name} must be a realistic non-negative integer.")

    def _matches_profile(self, criteria, profile):
        """Return whether a profile matches stored targeting criteria."""
        if (
            criteria.gender
            and criteria.gender != Gender.ANY
            and criteria.gender != profile.gender
        ):
            return False
        if criteria.age_min is not None and profile.age < criteria.age_min:
            return False
        if criteria.age_max is not None and profile.age > criteria.age_max:
            return False
        if criteria.region and criteria.region != profile.region:
            return False
        return True
