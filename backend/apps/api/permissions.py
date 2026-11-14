from rest_framework.permissions import BasePermission

from core.enums import AccountStatus, UserType


class IsRespondent(BasePermission):
    """Allows active authenticated respondent accounts only."""

    message = "Only active respondents can use this endpoint."

    def has_permission(self, request, view):
        """Return True for an active authenticated user with the respondent role."""
        user = request.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_active", True)
            and getattr(user, "user_type", None) == UserType.RESPONDENT
            and getattr(user, "account_status", AccountStatus.ACTIVE) == AccountStatus.ACTIVE
        )
