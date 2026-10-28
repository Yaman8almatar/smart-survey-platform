import sys
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class TokenAuthThrottle(AnonRateThrottle):
    """Rate limit login and token exchange requests."""

    scope = "auth_token"

    def allow_request(self, request, view):
        if getattr(settings, "ENABLE_THROTTLING_IN_TESTS", False):
            return super().allow_request(request, view)
        if (
            getattr(settings, "TESTING", False)
            or getattr(settings, "DISABLE_THROTTLING", False)
            or "pytest" in sys.modules
        ):
            return True
        return super().allow_request(request, view)


class RegisterThrottle(AnonRateThrottle):
    """Rate limit account registration requests."""

    scope = "auth_register"

    def allow_request(self, request, view):
        if getattr(settings, "ENABLE_THROTTLING_IN_TESTS", False):
            return super().allow_request(request, view)
        if (
            getattr(settings, "TESTING", False)
            or getattr(settings, "DISABLE_THROTTLING", False)
            or "pytest" in sys.modules
        ):
            return True
        return super().allow_request(request, view)
