import logging

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core import exceptions as core_exceptions

logger = logging.getLogger(__name__)

# Single place that maps platform exceptions to HTTP status and error code.
CORE_ERRORS = {
    core_exceptions.SurveyNotFound: (404, "survey_not_found"),
    core_exceptions.QuestionNotFound: (404, "question_not_found"),
    core_exceptions.AccountNotFound: (404, "account_not_found"),
    core_exceptions.ResponseNotFound: (404, "response_not_found"),
    core_exceptions.TargetingCriteriaNotFound: (404, "targeting_criteria_not_found"),
    core_exceptions.UnauthorizedAction: (403, "unauthorized_action"),
    core_exceptions.DuplicateResponse: (409, "duplicate_response"),
    core_exceptions.NotEditable: (409, "not_editable"),
    core_exceptions.ValidationError: (400, "validation_error"),
    core_exceptions.InvalidCredentials: (401, "invalid_credentials"),
    core_exceptions.ExternalAnalysisServiceError: (502, "external_service_error"),
}


def api_exception_handler(exc, context):
    """Return every API error as {"error": {"code", "message", "fields"?}}."""
    for exception_class, (status, code) in CORE_ERRORS.items():
        if isinstance(exc, exception_class):
            return Response(_error_body(code, str(exc)), status=status)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.error("Unhandled API exception.", exc_info=exc)
        return Response(
            _error_body("internal_error", "Unexpected server error."),
            status=500,
        )

    response.data = _drf_error_body(exc, response.data)
    return response


def _drf_error_body(exc, data):
    """Convert DRF error data into the shared error shape."""
    if isinstance(exc, drf_exceptions.ValidationError):
        fields = _plain(data) if isinstance(data, dict) else None
        message = "Invalid input." if fields else _first_message(data)
        return _error_body("validation_error", message, fields)

    code = getattr(exc, "default_code", "error")
    message = data.get("detail", exc.default_detail) if isinstance(data, dict) else data
    return _error_body(code, str(message))


def _error_body(code, message, fields=None):
    """Build the error envelope; fields is omitted when empty."""
    error = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


def _first_message(data):
    """Return the first message of a non-field validation error."""
    return str(data[0]) if isinstance(data, list) and data else "Invalid input."


def _plain(value):
    """Convert DRF ErrorDetail structures to plain JSON types."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return str(value)
