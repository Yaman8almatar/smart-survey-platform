class SmartSurveyException(Exception):
    """Base exception for Smart Survey Platform errors."""


class AccountNotFound(SmartSurveyException):
    """Raised when a user account cannot be found."""


class InvalidCredentials(SmartSurveyException):
    """Raised when login credentials are invalid."""


class UnauthorizedAction(SmartSurveyException):
    """Raised when a user is not allowed to perform an action."""


class SurveyNotFound(SmartSurveyException):
    """Raised when a survey cannot be found."""


class NotEditable(SmartSurveyException):
    """Raised when an entity cannot be edited in its current state."""


class DuplicateResponse(SmartSurveyException):
    """Raised when a respondent already submitted a response."""


class TargetingCriteriaNotFound(SmartSurveyException):
    """Raised when targeting criteria cannot be found."""


class QuestionNotFound(SmartSurveyException):
    """Raised when a survey question cannot be found."""


class ResponseNotFound(SmartSurveyException):
    """Raised when a survey response cannot be found."""


class ExternalAnalysisServiceError(SmartSurveyException):
    """Raised when the external sentiment analysis service fails."""


class ValidationError(SmartSurveyException):
    """Raised when business validation fails."""