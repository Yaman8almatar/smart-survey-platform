from apps.core.models import RespondentProfile
from core.enums import (
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    UserType,
)
from core.exceptions import UnauthorizedAction, ValidationError
from repositories.profile_repository import ProfileRepository

# Optional profile lists: field name, enum, and the error that names the field.
OPTIONAL_LISTS = (
    ("education", Education, "Choose an education level from the list."),
    ("occupation", Occupation, "Choose an occupation from the list."),
    ("marital_status", MaritalStatus, "Choose a marital status from the list."),
)


class ProfileService:
    """Handles respondent Profile management rules."""

    MIN_AGE = 1
    MAX_AGE = 120

    def __init__(self, profile_repository=None):
        """Wire the repository used for respondent profile persistence."""
        self.profile_repository = profile_repository or ProfileRepository()

    def get_profile(self, respondent_user):
        """Return the demographic profile for a respondent user."""
        self._ensure_respondent(respondent_user)
        return self.profile_repository.find_by_user_id(respondent_user.user_id)

    def update_profile(
        self,
        respondent_user,
        age,
        gender,
        region,
        interests,
        education=None,
        occupation=None,
        marital_status=None,
    ):
        """Create or update the profile; an optional value of None keeps the stored one."""
        self._ensure_respondent(respondent_user)
        self.validate_profile_data(
            age, gender, region, interests, education, occupation, marital_status
        )

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None:
            profile = RespondentProfile(user=respondent_user)

        profile.update_profile(
            age, gender, region, interests, education, occupation, marital_status
        )

        if profile.profile_id:
            return self.profile_repository.update(profile)
        return self.profile_repository.save(profile)

    def options(self):
        """Return the fixed profile lists as code and label pairs in list order."""
        return {
            "governorates": self._choice_list(Governorate),
            "education": self._choice_list(Education),
            "occupation": self._choice_list(Occupation),
            "marital_status": self._choice_list(MaritalStatus),
            "interests": self._choice_list(Interest),
        }

    def validate_profile_data(
        self,
        age,
        gender,
        region,
        interests,
        education=None,
        occupation=None,
        marital_status=None,
    ):
        """Validate profile values; the single rule set for registration and updates."""
        if type(age) is not int or age < self.MIN_AGE or age > self.MAX_AGE:
            raise ValidationError("Age must be a realistic positive integer.")

        # Gender.ANY is reserved for Targeting criteria, not respondent profiles.
        if gender == Gender.ANY:
            raise ValidationError("Gender.ANY is not allowed for respondent profiles.")
        if gender not in {Gender.MALE, Gender.FEMALE}:
            raise ValidationError("Gender must be MALE or FEMALE.")

        if not isinstance(region, str) or region not in Governorate.values:
            raise ValidationError("Choose a governorate from the list.")

        self._validate_interests(interests)

        optional_values = {
            "education": education,
            "occupation": occupation,
            "marital_status": marital_status,
        }
        for field_name, choices, message in OPTIONAL_LISTS:
            value = optional_values[field_name]
            # None keeps the stored value and "" means not answered.
            if value is None or value == "":
                continue
            if not isinstance(value, str) or value not in choices.values:
                raise ValidationError(message)

    def _validate_interests(self, interests):
        """Validate a list of 1 to 12 distinct interest codes."""
        if not isinstance(interests, (list, tuple)) or not interests:
            raise ValidationError("Choose at least one interest.")

        if any(
            not isinstance(code, str) or code not in Interest.values for code in interests
        ):
            raise ValidationError("Choose interests from the list.")

        # Distinct values of a 12-item list also cap the count at 12.
        if len(set(interests)) != len(interests):
            raise ValidationError("Choose each interest only once.")

    def _choice_list(self, choices):
        """Return one enum as a list of code and label pairs."""
        return [{"code": code, "label": label} for code, label in choices.choices]

    def _ensure_respondent(self, user):
        """Ensure only respondent accounts access profile operations."""
        if user.user_type != UserType.RESPONDENT:
            raise UnauthorizedAction("Only respondents can access profile data.")
