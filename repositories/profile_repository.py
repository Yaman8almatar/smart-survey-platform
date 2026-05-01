from apps.core.models import RespondentProfile


class ProfileRepository:
    """Provides database access for respondent demographic profiles."""

    def save(self, profile):
        """Persist a respondent profile."""
        profile.save()
        return profile

    def find_by_user_id(self, user_id):
        """Return the respondent profile for a user."""
        return RespondentProfile.objects.filter(user_id=user_id).first()

    def update(self, profile):
        """Persist changes to a respondent profile."""
        profile.save()
        return profile
