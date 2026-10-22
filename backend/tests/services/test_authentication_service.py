import pytest

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
