import pytest
from django.db import IntegrityError

from core.enums import AccountStatus, Gender, UserType
from core.exceptions import InvalidCredentials, ValidationError
from repositories.profile_repository import ProfileRepository
from repositories.user_repository import UserRepository
from services.authentication_service import AuthenticationService


@pytest.fixture
def auth_service():
    return AuthenticationService()


@pytest.mark.django_db
def test_register_service_provider_successfully(auth_service):
    user = auth_service.register_service_provider(
        name="Provider User",
        email="provider@example.com",
        password="strong-password",
    )

    assert user.user_type == UserType.SERVICE_PROVIDER
    assert user.account_status == AccountStatus.ACTIVE
    assert user.check_password("strong-password")


@pytest.mark.django_db
def test_register_respondent_successfully(auth_service):
    user = auth_service.register_respondent(
        name="Respondent User",
        email="respondent@example.com",
        password="strong-password",
        age=30,
        gender=Gender.FEMALE,
        region="Damascus",
        interests="Technology",
    )
    profile = ProfileRepository().find_by_user_id(user.user_id)

    assert user.user_type == UserType.RESPONDENT
    assert profile is not None
    assert profile.gender == Gender.FEMALE


@pytest.mark.django_db
def test_duplicate_email_registration_is_rejected(auth_service):
    auth_service.register_service_provider(
        name="Provider User",
        email="duplicate@example.com",
        password="strong-password",
    )

    with pytest.raises(ValidationError):
        auth_service.register_respondent(
            name="Respondent User",
            email="duplicate@example.com",
            password="strong-password",
            age=25,
            gender=Gender.MALE,
            region="Aleppo",
            interests="Sports",
        )


@pytest.mark.django_db
def test_authenticate_with_valid_credentials_succeeds(auth_service):
    auth_service.register_service_provider(
        name="Provider User",
        email="login@example.com",
        password="strong-password",
    )

    user = auth_service.authenticate_user("login@example.com", "strong-password")

    assert user.email == "login@example.com"


@pytest.mark.django_db
def test_authenticate_ignores_email_letter_case_and_spaces(auth_service):
    auth_service.register_service_provider(
        name="Provider User",
        email="case-login@example.com",
        password="strong-password",
    )

    user = auth_service.authenticate_user("  Case-Login@EXAMPLE.com ", "strong-password")

    assert user.email == "case-login@example.com"


@pytest.mark.django_db
def test_registration_stores_lowercase_email_and_rejects_other_case(auth_service):
    user = auth_service.register_service_provider(
        name="Provider User",
        email="  Case-Register@Example.COM ",
        password="strong-password",
    )

    with pytest.raises(ValidationError, match="Email is already registered."):
        auth_service.register_respondent(
            name="Respondent User",
            email="CASE-REGISTER@example.com",
            password="strong-password",
            age=25,
            gender=Gender.MALE,
            region="Aleppo",
            interests="Sports",
        )

    assert user.email == "case-register@example.com"


@pytest.mark.django_db
def test_authenticate_with_wrong_password_fails(auth_service):
    auth_service.register_service_provider(
        name="Provider User",
        email="wrong-password@example.com",
        password="strong-password",
    )

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user("wrong-password@example.com", "bad-password")


@pytest.mark.django_db
def test_suspended_account_authentication_fails(auth_service):
    user = auth_service.register_service_provider(
        name="Provider User",
        email="suspended@example.com",
        password="strong-password",
    )
    user.account_status = AccountStatus.SUSPENDED
    UserRepository().update(user)

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user("suspended@example.com", "strong-password")


@pytest.mark.django_db
def test_deleted_account_authentication_fails(auth_service):
    user = auth_service.register_service_provider(
        name="Provider User",
        email="deleted@example.com",
        password="strong-password",
    )
    user.account_status = AccountStatus.DELETED
    UserRepository().update(user)

    with pytest.raises(InvalidCredentials):
        auth_service.authenticate_user("deleted@example.com", "strong-password")


@pytest.mark.django_db
def test_respondent_registration_rejects_gender_any(auth_service):
    with pytest.raises(ValidationError):
        auth_service.register_respondent(
            name="Respondent User",
            email="any-gender@example.com",
            password="strong-password",
            age=30,
            gender=Gender.ANY,
            region="Damascus",
            interests="Technology",
        )


class FailingProfileRepository(ProfileRepository):
    def save(self, profile):
        raise RuntimeError("Profile storage failed.")


@pytest.mark.django_db
def test_respondent_registration_rolls_back_user_when_profile_save_fails():
    service = AuthenticationService(profile_repository=FailingProfileRepository())

    with pytest.raises(RuntimeError):
        service.register_respondent(
            name="Respondent User",
            email="respondent-rollback@example.com",
            password="strong-password",
            age=30,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
        )

    assert not UserRepository().email_exists("respondent-rollback@example.com")


@pytest.mark.django_db
def test_provider_email_constraint_reports_registered_email(auth_service, monkeypatch):
    auth_service.register_service_provider(
        name="Provider User",
        email="race-provider@example.com",
        password="strong-password",
    )
    # Skip the pre-check so only the users_email constraint can catch the duplicate.
    monkeypatch.setattr(auth_service.user_repository, "email_exists", lambda email: False)

    with pytest.raises(ValidationError, match="Email is already registered."):
        auth_service.register_service_provider(
            name="Provider User",
            email="race-provider@example.com",
            password="strong-password",
        )


@pytest.mark.django_db
def test_respondent_email_constraint_reports_registered_email(auth_service, monkeypatch):
    details = {
        "name": "Respondent User",
        "email": "race-respondent@example.com",
        "password": "strong-password",
        "age": 30,
        "gender": Gender.FEMALE,
        "region": "Damascus",
        "interests": "Technology",
    }
    auth_service.register_respondent(**details)
    # Skip the pre-check so only the users_email constraint can catch the duplicate.
    monkeypatch.setattr(auth_service.user_repository, "email_exists", lambda email: False)

    with pytest.raises(ValidationError, match="Email is already registered."):
        auth_service.register_respondent(**details)


def _fail_with_other_constraint(user):
    raise IntegrityError(
        'null value in column "name" of relation "users" violates not-null constraint'
    )


@pytest.mark.django_db
def test_provider_registration_reraises_other_integrity_error(auth_service, monkeypatch):
    monkeypatch.setattr(auth_service.user_repository, "save", _fail_with_other_constraint)

    with pytest.raises(IntegrityError):
        auth_service.register_service_provider(
            name="Provider User",
            email="other-provider@example.com",
            password="strong-password",
        )


@pytest.mark.django_db
def test_respondent_registration_reraises_other_integrity_error(auth_service, monkeypatch):
    monkeypatch.setattr(auth_service.user_repository, "save", _fail_with_other_constraint)

    with pytest.raises(IntegrityError):
        auth_service.register_respondent(
            name="Respondent User",
            email="other-respondent@example.com",
            password="strong-password",
            age=30,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
        )
