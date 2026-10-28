from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from apps.core.models import RespondentProfile, User
from core.enums import AccountStatus, Gender, UserType
from core.exceptions import InvalidCredentials, ValidationError
from repositories.profile_repository import ProfileRepository
from repositories.user_repository import UserRepository


class AuthenticationService:
    """Coordinates account registration and Authentication flow credential checks."""

    def __init__(self, user_repository=None, profile_repository=None):
        """Wire repositories used by authentication and registration workflows."""
        self.user_repository = user_repository or UserRepository()
        self.profile_repository = profile_repository or ProfileRepository()

    def register_service_provider(self, name, email, password):
        """Register a service provider account with a hashed password."""
        normalized_email = self._normalize_email(email)
        self._reject_duplicate_email(normalized_email)

        user = User(
            name=name,
            email=normalized_email,
            user_type=UserType.SERVICE_PROVIDER,
            account_status=AccountStatus.ACTIVE,
        )
        self._validate_user_password(password, user=user)
        user.set_password(password)
        try:
            return self.user_repository.save(user)
        except IntegrityError as exc:
            raise ValidationError("Email is already registered.") from exc

    def register_respondent(self, name, email, password, age, gender, region, interests):
        """Register a respondent account and create its demographic profile."""
        # Gender.ANY is reserved for Targeting criteria, not respondent profiles.
        if gender == Gender.ANY:
            raise ValidationError("Gender.ANY is not allowed for respondent profiles.")

        normalized_email = self._normalize_email(email)
        self._reject_duplicate_email(normalized_email)

        user = User(
            name=name,
            email=normalized_email,
            user_type=UserType.RESPONDENT,
            account_status=AccountStatus.ACTIVE,
        )
        self._validate_user_password(password, user=user)
        user.set_password(password)

        try:
            with transaction.atomic():
                # A respondent account is never stored without its profile.
                saved_user = self.user_repository.save(user)

                profile = RespondentProfile(
                    user=saved_user,
                    age=age,
                    gender=gender,
                    region=region,
                    interests=interests,
                )
                self.profile_repository.save(profile)
            return saved_user
        except IntegrityError as exc:
            raise ValidationError("Email is already registered.") from exc

    def authenticate_user(self, email, password):
        """Authenticate an active user by email and password."""
        normalized_email = self._normalize_email(email)
        user = self.user_repository.find_by_email(normalized_email)

        if user is None or not user.check_password(password):
            raise InvalidCredentials("Invalid email or password.")

        if user.account_status in {AccountStatus.SUSPENDED, AccountStatus.DELETED}:
            raise InvalidCredentials("Account is suspended or deleted.")

        return user

    def _normalize_email(self, email):
        """Normalize email address to lowercase and strip whitespace."""
        return email.strip().lower() if isinstance(email, str) else ""

    def _validate_user_password(self, password, user=None):
        """Validate password against Django's AUTH_PASSWORD_VALIDATORS."""
        try:
            validate_password(password, user=user)
        except DjangoValidationError as err:
            raise ValidationError(", ".join(err.messages))

    def _reject_duplicate_email(self, email):
        """Reject registration when the email is already used."""
        if self.user_repository.email_exists(email):
            raise ValidationError("Email is already registered.")
