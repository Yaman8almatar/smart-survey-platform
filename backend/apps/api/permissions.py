from rest_framework.permissions import BasePermission

from core.enums import UserType


class IsRespondent(BasePermission):
    """Allows authenticated respondent accounts only."""

    message = "Only respondents can use this endpoint."

    def has_permission(self, request, view):
        """Return True for an authenticated user with the respondent role."""
        user = request.user
        return bool(
            user and user.is_authenticated and user.user_type == UserType.RESPONDENT
        )
