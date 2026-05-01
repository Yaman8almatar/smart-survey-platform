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
        self._reject_duplicate_email(email)

        user = User(
            name=name,
            email=email,
            user_type=UserType.SERVICE_PROVIDER,
            account_status=AccountStatus.ACTIVE,
        )
        user.set_password(password)
        return self.user_repository.save(user)

    def register_respondent(self, name, email, password, age, gender, region, interests):
        """Register a respondent account and create its demographic profile."""
        # Gender.ANY is reserved for Targeting criteria, not respondent profiles.
        if gender == Gender.ANY:
            raise ValidationError("Gender.ANY is not allowed for respondent profiles.")

        self._reject_duplicate_email(email)

        user = User(
            name=name,
            email=email,
            user_type=UserType.RESPONDENT,
            account_status=AccountStatus.ACTIVE,
        )
        user.set_password(password)
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

    def authenticate_user(self, email, password):
        """Authenticate an active user by email and password."""
        user = self.user_repository.find_by_email(email)

        if user is None or not user.check_password(password):
            raise InvalidCredentials("Invalid email or password.")

        if user.account_status in {AccountStatus.SUSPENDED, AccountStatus.DELETED}:
            raise InvalidCredentials("Account is suspended or deleted.")

        return user

    def _reject_duplicate_email(self, email):
        """Reject registration when the email is already used."""
        if self.user_repository.email_exists(email):
            raise ValidationError("Email is already registered.")
