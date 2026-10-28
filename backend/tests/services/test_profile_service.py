import pytest

from apps.core.models import RespondentProfile, User
from core.enums import AccountStatus, Gender, UserType
from core.exceptions import UnauthorizedAction, ValidationError
from repositories.profile_repository import ProfileRepository
from services.profile_service import ProfileService


@pytest.fixture
def profile_service():
    return ProfileService()


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.mark.django_db
def test_respondent_can_get_existing_profile(profile_service):
    user = create_user("respondent-get@example.com", UserType.RESPONDENT)
    profile = RespondentProfile(
        user=user,
        age=28,
        gender=Gender.FEMALE,
        region="Damascus",
        interests="Technology",
    )
    ProfileRepository().save(profile)

    result = profile_service.get_profile(user)

    assert result == profile


@pytest.mark.django_db
def test_respondent_can_update_existing_profile(profile_service):
    user = create_user("respondent-update@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=user,
            age=28,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
        )
    )

    profile = profile_service.update_profile(
        user,
        age=35,
        gender=Gender.MALE,
        region="Aleppo",
        interests="Sports",
    )

    assert profile.age == 35
    assert profile.gender == Gender.MALE
    assert profile.region == "Aleppo"
    assert profile.interests == "Sports"


@pytest.mark.django_db
def test_respondent_can_create_profile_if_missing(profile_service):
    user = create_user("respondent-create@example.com", UserType.RESPONDENT)

    profile = profile_service.update_profile(
        user,
        age=31,
        gender=Gender.FEMALE,
        region="Homs",
        interests="Reading",
    )

    assert profile.profile_id is not None
    assert profile.user == user
    assert profile.age == 31


@pytest.mark.django_db
def test_non_respondent_user_cannot_get_profile(profile_service):
    user = create_user("provider-get@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        profile_service.get_profile(user)


@pytest.mark.django_db
def test_non_respondent_user_cannot_update_profile(profile_service):
    user = create_user("provider-update@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        profile_service.update_profile(
            user,
            age=40,
            gender=Gender.MALE,
            region="Latakia",
            interests="Business",
        )


@pytest.mark.django_db
def test_gender_any_is_rejected(profile_service):
    user = create_user("respondent-any@example.com", UserType.RESPONDENT)

    with pytest.raises(ValidationError):
        profile_service.update_profile(
            user,
            age=30,
            gender=Gender.ANY,
            region="Damascus",
            interests="Technology",
        )


@pytest.mark.django_db
@pytest.mark.parametrize("age", [0, -1, 121, "30"])
def test_invalid_age_is_rejected(profile_service, age):
    user = create_user(f"respondent-age-{age}@example.com", UserType.RESPONDENT)

    with pytest.raises(ValidationError):
        profile_service.update_profile(
            user,
            age=age,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
        )
