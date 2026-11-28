"""FR-12: a survey reaches respondents only through admin approval; tests publish this way."""

from itertools import count

from apps.core.models import User
from core.enums import AccountStatus, UserType
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService

_admin_numbers = count(1)


def create_admin(email=None):
    """Create an active admin user; a fresh email by default."""
    return User.objects.create_user(
        email=email or f"review-admin-{next(_admin_numbers)}@example.com",
        password="strong-password",
        name="Review Admin",
        user_type=UserType.ADMIN,
        account_status=AccountStatus.ACTIVE,
    )


def publish_through_review(provider, survey_id):
    """Submit the provider's draft, approve it as a new admin, and return the survey."""
    SurveyService().submit_for_review(provider, survey_id)
    return SurveyReviewService().approve(create_admin(), survey_id)
