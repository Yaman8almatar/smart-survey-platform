from django.db.models import Q

from apps.core.models import RespondentProfile, TargetingCriteria
from core.enums import AccountStatus, Gender, Governorate, UserType


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

    def count_pool(self):
        """Return the number of active respondents with a complete profile (one COUNT)."""
        return self._pool().count()

    def count_matching(self, criteria):
        """Return how many pool profiles match criteria, saved or not (P-17, count form).

        TargetingService.profile_matches_criteria is the Python form and
        SurveyRepository.find_eligible_for_respondent the survey-query form; the parity
        test in test_survey_service.py keeps the three equal (P-18). One COUNT query.
        """
        profiles = self._pool()
        if criteria.gender in {Gender.MALE, Gender.FEMALE}:
            profiles = profiles.filter(gender=criteria.gender)
        if criteria.age_min is not None:
            profiles = profiles.filter(age__gte=criteria.age_min)
        if criteria.age_max is not None:
            profiles = profiles.filter(age__lte=criteria.age_max)
        for list_name, profile_field in TargetingCriteria.SINGLE_VALUE_LISTS:
            allowed = list(getattr(criteria, list_name))
            if allowed:
                profiles = profiles.filter(**{f"{profile_field}__in": allowed})
        if criteria.interests:
            profiles = profiles.filter(interests__overlap=list(criteria.interests))
        return profiles.count()

    def _pool(self):
        """Profiles that can be reached: an active respondent account, a complete profile.

        "Complete" is RespondentProfile.is_complete as a query; "active" is the check of
        apps.api.permissions.IsRespondent.
        """
        return RespondentProfile.objects.filter(
            ~Q(gender=""),
            ~Q(interests=[]),
            user__user_type=UserType.RESPONDENT,
            user__account_status=AccountStatus.ACTIVE,
            user__is_active=True,
            age__gt=0,
            region__in=Governorate.values,
        )
