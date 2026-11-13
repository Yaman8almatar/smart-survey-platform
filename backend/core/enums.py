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


# Sentence-case display labels for web pages. QuestionType's own labels stay
# unchanged because they are part of the model field's choices (a change
# would need a migration).
QUESTION_TYPE_LABELS = {
    QuestionType.MULTIPLE_CHOICE: "Multiple choice",
    QuestionType.RATING_SCALE: "Rating scale",
    QuestionType.OPEN_TEXT: "Open text",
}


class Gender(models.TextChoices):
    """Defines gender values used by profiles and targeting criteria."""

    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    ANY = "ANY", "Any"


class Governorate(models.TextChoices):
    """Defines the fixed governorate list used by profiles and targeting criteria."""

    ALEPPO = "ALEPPO", "Aleppo"
    AL_HASAKAH = "AL_HASAKAH", "Al-Hasakah"
    AS_SUWAYDA = "AS_SUWAYDA", "As-Suwayda"
    DAMASCUS = "DAMASCUS", "Damascus"
    DARAA = "DARAA", "Daraa"
    DEIR_EZ_ZOR = "DEIR_EZ_ZOR", "Deir ez-Zor"
    HAMA = "HAMA", "Hama"
    HOMS = "HOMS", "Homs"
    IDLIB = "IDLIB", "Idlib"
    LATAKIA = "LATAKIA", "Latakia"
    QUNEITRA = "QUNEITRA", "Quneitra"
    RAQQA = "RAQQA", "Raqqa"
    RIF_DIMASHQ = "RIF_DIMASHQ", "Rif Dimashq"
    TARTUS = "TARTUS", "Tartus"
    OUTSIDE_SYRIA = "OUTSIDE_SYRIA", "Outside Syria"


class Education(models.TextChoices):
    """Defines the optional education levels of a respondent profile."""

    BASIC = "BASIC", "Basic education or less"
    SECONDARY = "SECONDARY", "Secondary school"
    INSTITUTE = "INSTITUTE", "Institute diploma"
    BACHELOR = "BACHELOR", "Bachelor's degree"
    MASTER = "MASTER", "Master's degree"
    DOCTORATE = "DOCTORATE", "Doctorate"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"


class Occupation(models.TextChoices):
    """Defines the optional occupations of a respondent profile."""

    STUDENT = "STUDENT", "Student"
    PUBLIC_SECTOR = "PUBLIC_SECTOR", "Public sector employee"
    PRIVATE_SECTOR = "PRIVATE_SECTOR", "Private sector employee"
    SELF_EMPLOYED = "SELF_EMPLOYED", "Self-employed or business owner"
    LOOKING_FOR_WORK = "LOOKING_FOR_WORK", "Looking for work"
    HOMEMAKER = "HOMEMAKER", "Homemaker"
    RETIRED = "RETIRED", "Retired"
    OTHER = "OTHER", "Other"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"


class MaritalStatus(models.TextChoices):
    """Defines the optional marital status values of a respondent profile."""

    SINGLE = "SINGLE", "Single"
    MARRIED = "MARRIED", "Married"
    DIVORCED = "DIVORCED", "Divorced"
    WIDOWED = "WIDOWED", "Widowed"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"


class Interest(models.TextChoices):
    """Defines the fixed interest topics a respondent can choose."""

    TECHNOLOGY = "TECHNOLOGY", "Technology"
    EDUCATION = "EDUCATION", "Education"
    HEALTH = "HEALTH", "Health"
    SPORTS = "SPORTS", "Sports"
    FOOD = "FOOD", "Food and cooking"
    TRAVEL = "TRAVEL", "Travel"
    SHOPPING = "SHOPPING", "Shopping"
    FINANCE = "FINANCE", "Money and finance"
    CAREERS = "CAREERS", "Jobs and careers"
    ARTS = "ARTS", "Arts and culture"
    ENTERTAINMENT = "ENTERTAINMENT", "Entertainment"
    ENVIRONMENT = "ENVIRONMENT", "Environment"


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
