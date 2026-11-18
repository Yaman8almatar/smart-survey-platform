from apps.core.models import TargetingCriteria
from core.enums import (
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    UserType,
)
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services import disclosure


class TargetingService:
    """Handles Targeting criteria persistence and respondent matching."""

    MAX_AGE = 120
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

    # Criteria list -> (enum, error message). Validation order follows this tuple.
    LIST_CHOICES = (
        ("regions", Governorate, "Choose governorates from the list."),
        ("education_levels", Education, "Choose education levels from the list."),
        ("occupations", Occupation, "Choose occupations from the list."),
        ("marital_statuses", MaritalStatus, "Choose marital statuses from the list."),
        ("interests", Interest, "Choose interests from the list."),
    )

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
        regions=(),
        education_levels=(),
        occupations=(),
        marital_statuses=(),
        interests=(),
    ):
        """Create or update targeting criteria for an owned draft survey."""
        survey = self._get_owned_draft_survey(provider_user, survey_id)
        criteria = self.build_criteria(
            gender=gender,
            age_min=age_min,
            age_max=age_max,
            regions=regions,
            education_levels=education_levels,
            occupations=occupations,
            marital_statuses=marital_statuses,
            interests=interests,
        )
        return self.targeting_repository.create_or_update(
            survey=survey,
            gender=criteria.gender,
            age_min=criteria.age_min,
            age_max=criteria.age_max,
            **{name: getattr(criteria, name) for name, _, _ in self.LIST_CHOICES},
        )

    def build_criteria(
        self,
        gender=None,
        age_min=None,
        age_max=None,
        regions=(),
        education_levels=(),
        occupations=(),
        marital_statuses=(),
        interests=(),
    ):
        """Validate criteria values and return them as an unsaved TargetingCriteria.

        save_criteria stores what this returns, so saved and previewed criteria are
        validated by the same code.
        """
        self._validate_criteria(gender, age_min, age_max)
        lists = self._clean_lists(
            {
                "regions": regions,
                "education_levels": education_levels,
                "occupations": occupations,
                "marital_statuses": marital_statuses,
                "interests": interests,
            }
        )
        return TargetingCriteria(gender=gender, age_min=age_min, age_max=age_max, **lists)

    def reach(self, provider_user, survey_id, **criteria_values):
        """Return the banded reach of possibly unsaved criteria for an owned draft survey."""
        self._get_owned_draft_survey(provider_user, survey_id)
        return self.describe_reach(self.build_criteria(**criteria_values))

    def describe_reach(self, criteria):
        """Return {"state", "count", "total", "percent"} for criteria (P-19).

        state is "everyone" for open criteria, else the disclosure band's state with
        "exact" renamed "narrowed"; a count of 1 to 4 is never returned as a number.
        """
        total = self.profile_repository.count_pool()
        if criteria.is_open_to_all():
            state, count = "everyone", total
        else:
            banded = disclosure.band(self.profile_repository.count_matching(criteria))
            state = "narrowed" if banded["state"] == "exact" else banded["state"]
            count = banded["count"]
        percent = None
        if state in {"everyone", "narrowed"} and total > 0:
            percent = round(100 * count / total)
        return {"state": state, "count": count, "total": total, "percent": percent}

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

        return self.profile_matches_criteria(criteria, profile)

    def get_criteria_initial(self, provider_user, survey_id):
        """Return targeting criteria values for pre-filling the targeting form."""
        self._get_owned_survey(provider_user, survey_id)
        criteria = self.targeting_repository.find_by_survey_id(survey_id)

        if criteria is None:
            return {}

        return self.criteria_values(criteria)

    def criteria_values(self, criteria):
        """Return criteria as plain values for forms and display."""
        return {
            "gender": criteria.gender or "",
            "age_min": criteria.age_min,
            "age_max": criteria.age_max,
            "regions": list(criteria.regions),
            "education_levels": list(criteria.education_levels),
            "occupations": list(criteria.occupations),
            "marital_statuses": list(criteria.marital_statuses),
            "interests": list(criteria.interests),
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

    def _validate_criteria(self, gender, age_min, age_max):
        """Validate demographic targeting criteria before saving."""
        # Gender.ANY is valid here because it means no gender restriction.
        if gender not in {None, Gender.MALE, Gender.FEMALE, Gender.ANY}:
            raise ValidationError("Gender must be MALE, FEMALE, ANY, or None.")

        self._validate_age("age_min", age_min)
        self._validate_age("age_max", age_max)

        if age_min is not None and age_max is not None and age_min > age_max:
            raise ValidationError("Minimum age must be less than or equal to maximum age.")

    def _clean_lists(self, raw_lists):
        """Validate each criteria list against its enum and drop duplicates, first order kept."""
        cleaned = {}
        for name, enum, message in self.LIST_CHOICES:
            values = []
            for value in raw_lists[name] or ():
                # PREFER_NOT_TO_SAY is a profile answer, never a targeting choice.
                if value not in enum.values or value == self.PREFER_NOT_TO_SAY:
                    raise ValidationError(message)
                if value not in values:
                    values.append(value)
            cleaned[name] = values
        return cleaned

    def _validate_age(self, field_name, age):
        """Validate optional targeting age bounds."""
        if age is None:
            return

        if type(age) is not int or age < 0 or age > self.MAX_AGE:
            raise ValidationError(f"{field_name} must be a realistic non-negative integer.")

    def profile_matches_criteria(self, criteria, profile):
        """Return whether a profile matches stored targeting criteria (P-17, Python form).

        SurveyRepository.find_eligible_for_respondent holds the same rule as a query; the
        parity test in test_survey_service.py keeps the two forms equal (P-18). Fields
        combine with AND; an unset value or an empty list means no restriction.
        """
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
        # A profile value of "" or PREFER_NOT_TO_SAY is never in a saved list, so it fails
        # any non-empty list for that detail.
        for list_name, profile_field in TargetingCriteria.SINGLE_VALUE_LISTS:
            allowed = getattr(criteria, list_name)
            if allowed and getattr(profile, profile_field) not in allowed:
                return False
        if criteria.interests and not set(criteria.interests) & set(profile.interests):
            return False
        return True
