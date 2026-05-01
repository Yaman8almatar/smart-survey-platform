from django.db import models


class UserType(models.TextChoices):
    """Defines platform roles used for authorization and navigation."""

    SERVICE_PROVIDER = "SERVICE_PROVIDER", "Service Provider"
    RESPONDENT = "RESPONDENT", "Respondent"
    ADMIN = "ADMIN", "Admin"


class AccountStatus(models.TextChoices):
    """Defines account lifecycle states used by authentication and admin actions."""

    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    DELETED = "DELETED", "Deleted"


class SurveyStatus(models.TextChoices):
    """Defines survey lifecycle states for editing, publishing, and closing."""

    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    CLOSED = "CLOSED", "Closed"


class QuestionType(models.TextChoices):
    """Defines supported survey question and answer formats."""

    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"
    RATING_SCALE = "RATING_SCALE", "Rating Scale"
    OPEN_TEXT = "OPEN_TEXT", "Open Text"


class Gender(models.TextChoices):
    """Defines gender values used by profiles and targeting criteria."""

    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    ANY = "ANY", "Any"


class SentimentLabel(models.TextChoices):
    """Defines normalized sentiment categories stored for open-text answers."""

    POSITIVE = "POSITIVE", "Positive"
    NEGATIVE = "NEGATIVE", "Negative"
    NEUTRAL = "NEUTRAL", "Neutral"


class AnalysisStatus(models.TextChoices):
    """Defines sentiment analysis processing states."""

    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
