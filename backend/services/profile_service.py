from apps.core.models import RespondentProfile
from core.enums import Gender, UserType
from core.exceptions import UnauthorizedAction, ValidationError
from repositories.profile_repository import ProfileRepository


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

    def update_profile(self, respondent_user, age, gender, region, interests):
        """Create or update the demographic profile for a respondent user."""
        self._ensure_respondent(respondent_user)
        self._validate_profile_data(age, gender)

        profile = self.profile_repository.find_by_user_id(respondent_user.user_id)
        if profile is None:
            profile = RespondentProfile(user=respondent_user)

        profile.update_profile(age, gender, region, interests)

        if profile.profile_id:
            return self.profile_repository.update(profile)
        return self.profile_repository.save(profile)

    def _ensure_respondent(self, user):
        """Ensure only respondent accounts access profile operations."""
        if user.user_type != UserType.RESPONDENT:
            raise UnauthorizedAction("Only respondents can access profile data.")

    def _validate_profile_data(self, age, gender):
        """Validate demographic profile values used for targeting."""
        if not isinstance(age, int) or age < self.MIN_AGE or age > self.MAX_AGE:
            raise ValidationError("Age must be a realistic positive integer.")

        if gender == Gender.ANY:
            raise ValidationError("Gender.ANY is not allowed for respondent profiles.")
