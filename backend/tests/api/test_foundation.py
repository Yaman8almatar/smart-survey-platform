import re
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.conf import settings
from rest_framework import exceptions as drf_exceptions

from apps.api.exceptions import api_exception_handler
from apps.api.permissions import IsRespondent
from config import settings as config_settings
from core import exceptions as core_exceptions
from core.enums import UserType


@pytest.mark.parametrize(
    ("exception", "status", "code"),
    [
        (core_exceptions.SurveyNotFound("x"), 404, "survey_not_found"),
        (core_exceptions.QuestionNotFound("x"), 404, "question_not_found"),
        (core_exceptions.AccountNotFound("x"), 404, "account_not_found"),
        (core_exceptions.ResponseNotFound("x"), 404, "response_not_found"),
        (
            core_exceptions.TargetingCriteriaNotFound("x"),
            404,
            "targeting_criteria_not_found",
        ),
        (core_exceptions.UnauthorizedAction("x"), 403, "unauthorized_action"),
        (core_exceptions.DuplicateResponse("x"), 409, "duplicate_response"),
        (core_exceptions.NotEditable("x"), 409, "not_editable"),
        (core_exceptions.ValidationError("x"), 400, "validation_error"),
        (core_exceptions.InvalidCredentials("x"), 401, "invalid_credentials"),
        (
            core_exceptions.ExternalAnalysisServiceError("x"),
            502,
            "external_service_error",
        ),
    ],
)
def test_core_exceptions_map_to_status_and_code(exception, status, code):
    response = api_exception_handler(exception, {})

    assert response.status_code == status
    assert response.data == {"error": {"code": code, "message": "x"}}


def test_unmapped_exception_returns_json_500():
    response = api_exception_handler(RuntimeError("boom"), {})

    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert "boom" not in response.data["error"]["message"]


def test_serializer_errors_become_fields():
    exception = drf_exceptions.ValidationError({"age": ["Too low."], "email": ["Bad."]})

    response = api_exception_handler(exception, {})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert response.data["error"]["fields"] == {
        "age": ["Too low."],
        "email": ["Bad."],
    }


@pytest.mark.parametrize(
    ("exception", "status", "code"),
    [
        (drf_exceptions.NotAuthenticated(), 401, "not_authenticated"),
        (drf_exceptions.AuthenticationFailed(), 401, "authentication_failed"),
        (drf_exceptions.PermissionDenied(), 403, "permission_denied"),
        (drf_exceptions.NotFound(), 404, "not_found"),
        (drf_exceptions.MethodNotAllowed("PATCH"), 405, "method_not_allowed"),
    ],
)
def test_drf_exceptions_use_the_same_shape(exception, status, code):
    response = api_exception_handler(exception, {})

    assert response.status_code == status
    assert set(response.data) == {"error"}
    assert response.data["error"]["code"] == code
    assert isinstance(response.data["error"]["message"], str)


def test_token_lifetimes_are_30_minutes_and_7_days():
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=30)
    assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(days=7)
    assert settings.SIMPLE_JWT["USER_ID_FIELD"] == "user_id"


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("http://localhost:5000", True),
        ("http://127.0.0.1:8080", True),
        ("http://localhost.evil.com:5000", False),
        ("https://localhost:5000", False),
        ("http://evil.com", False),
        ("http://127.0.0.1.evil.com:80", False),
    ],
)
def test_cors_regexes_allow_only_local_origins(origin, allowed):
    matched = any(
        re.match(pattern, origin) for pattern in settings.API_CORS_LOCAL_ORIGIN_REGEXES
    )

    assert matched is allowed


def test_cors_regexes_are_active_only_in_debug():
    # pytest-django forces settings.DEBUG off; the module value is what .env set.
    expected = config_settings.API_CORS_LOCAL_ORIGIN_REGEXES if config_settings.DEBUG else []

    assert settings.CORS_ALLOWED_ORIGIN_REGEXES == expected


@pytest.mark.parametrize(
    ("user", "allowed"),
    [
        (None, False),
        (SimpleNamespace(is_authenticated=False, user_type=None), False),
        (SimpleNamespace(is_authenticated=True, user_type=UserType.ADMIN), False),
        (
            SimpleNamespace(is_authenticated=True, user_type=UserType.SERVICE_PROVIDER),
            False,
        ),
        (SimpleNamespace(is_authenticated=True, user_type=UserType.RESPONDENT), True),
    ],
)
def test_is_respondent_permission(user, allowed):
    request = SimpleNamespace(user=user)

    assert IsRespondent().has_permission(request, None) is allowed


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/v1/schema/", "/api/v1/docs/"])
def test_schema_and_docs_are_public(client, path):
    response = client.get(path)

    assert response.status_code == 200
