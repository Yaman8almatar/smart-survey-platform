import pytest

from apps.core.models import RespondentProfile, User
from core.enums import (
    AccountStatus,
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    UserType,
)
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


def valid_details(**overrides):
    details = {
        "age": 30,
        "gender": Gender.FEMALE,
        "region": Governorate.DAMASCUS,
        "interests": [Interest.TECHNOLOGY],
    }
    details.update(overrides)
    return details


@pytest.mark.django_db
def test_respondent_can_get_existing_profile(profile_service):
    user = create_user("respondent-get@example.com", UserType.RESPONDENT)
    profile = RespondentProfile(
        user=user,
        age=28,
        gender=Gender.FEMALE,
        region=Governorate.DAMASCUS,
        interests=[Interest.TECHNOLOGY],
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
            region=Governorate.DAMASCUS,
            interests=[Interest.TECHNOLOGY],
        )
    )

    profile = profile_service.update_profile(
        user,
        age=35,
        gender=Gender.MALE,
        region=Governorate.ALEPPO,
        interests=[Interest.SPORTS, Interest.TRAVEL],
    )

    profile.refresh_from_db()
    assert profile.age == 35
    assert profile.gender == Gender.MALE
    assert profile.region == Governorate.ALEPPO
    assert profile.interests == [Interest.SPORTS, Interest.TRAVEL]


@pytest.mark.django_db
def test_respondent_can_create_profile_if_missing(profile_service):
    user = create_user("respondent-create@example.com", UserType.RESPONDENT)

    profile = profile_service.update_profile(user, **valid_details(age=31))

    assert profile.profile_id is not None
    assert profile.user == user
    assert profile.age == 31
    assert (profile.education, profile.occupation, profile.marital_status) == ("", "", "")


@pytest.mark.django_db
def test_non_respondent_user_cannot_get_profile(profile_service):
    user = create_user("provider-get@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        profile_service.get_profile(user)


@pytest.mark.django_db
def test_non_respondent_user_cannot_update_profile(profile_service):
    user = create_user("provider-update@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        profile_service.update_profile(user, **valid_details(gender=Gender.MALE))


@pytest.mark.django_db
def test_gender_any_is_rejected(profile_service):
    user = create_user("respondent-any@example.com", UserType.RESPONDENT)

    with pytest.raises(ValidationError):
        profile_service.update_profile(user, **valid_details(gender=Gender.ANY))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("region", "", "Choose a governorate from the list."),
        ("region", " DAMASCUS ", "Choose a governorate from the list."),
        ("region", "damascus", "Choose a governorate from the list."),
        ("region", "Damascus", "Choose a governorate from the list."),
        ("region", "AMMAN", "Choose a governorate from the list."),
        ("region", None, "Choose a governorate from the list."),
        ("interests", [], "Choose at least one interest."),
        ("interests", "TECHNOLOGY", "Choose at least one interest."),
        ("interests", None, "Choose at least one interest."),
        ("interests", ["READING"], "Choose interests from the list."),
        ("interests", [" TECHNOLOGY"], "Choose interests from the list."),
        ("interests", ["TECHNOLOGY", "TECHNOLOGY"], "Choose each interest only once."),
        ("education", "PHD", "Choose an education level from the list."),
        ("occupation", "ENGINEER", "Choose an occupation from the list."),
        ("marital_status", "ENGAGED", "Choose a marital status from the list."),
        ("age", True, "Age must be a realistic positive integer."),
    ],
)
def test_invalid_profile_field_is_rejected(profile_service, field, value, message):
    user = create_user(f"respondent-invalid-{field}@example.com", UserType.RESPONDENT)
    details = valid_details()
    details[field] = value

    with pytest.raises(ValidationError, match=message):
        profile_service.update_profile(user, **details)

    assert not RespondentProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_all_twelve_interests_are_accepted(profile_service):
    user = create_user("respondent-all-interests@example.com", UserType.RESPONDENT)

    profile = profile_service.update_profile(
        user, **valid_details(interests=list(Interest.values))
    )

    assert profile.interests == list(Interest.values)


@pytest.mark.django_db
@pytest.mark.parametrize("age", [0, -1, 121, "30"])
def test_invalid_age_is_rejected(profile_service, age):
    user = create_user(f"respondent-age-{age}@example.com", UserType.RESPONDENT)

    with pytest.raises(ValidationError):
        profile_service.update_profile(user, **valid_details(age=age))


@pytest.mark.django_db
def test_update_with_none_keeps_optional_values(profile_service):
    user = create_user("respondent-keep@example.com", UserType.RESPONDENT)
    profile_service.update_profile(
        user,
        **valid_details(),
        education=Education.BACHELOR,
        occupation=Occupation.STUDENT,
        marital_status=MaritalStatus.SINGLE,
    )

    profile_service.update_profile(user, **valid_details(age=33))

    profile = RespondentProfile.objects.get(user=user)
    assert profile.age == 33
    assert (profile.education, profile.occupation, profile.marital_status) == (
        Education.BACHELOR,
        Occupation.STUDENT,
        MaritalStatus.SINGLE,
    )


@pytest.mark.django_db
def test_update_with_empty_string_clears_optional_values(profile_service):
    user = create_user("respondent-clear@example.com", UserType.RESPONDENT)
    profile_service.update_profile(
        user,
        **valid_details(),
        education=Education.MASTER,
        occupation=Occupation.RETIRED,
        marital_status=MaritalStatus.MARRIED,
    )

    profile_service.update_profile(
        user, **valid_details(), education="", occupation="", marital_status=""
    )

    profile = RespondentProfile.objects.get(user=user)
    assert (profile.education, profile.occupation, profile.marital_status) == ("", "", "")


def profile_with(**values):
    return RespondentProfile(**{"age": None, "gender": "", "region": "", **values})


@pytest.mark.parametrize(
    ("values", "percent"),
    [
        ({}, 0),
        (
            {
                "age": 30,
                "gender": Gender.FEMALE,
                "region": Governorate.HOMS,
                "interests": [Interest.HEALTH],
            },
            57,
        ),
        (
            {
                "age": 30,
                "gender": Gender.FEMALE,
                "region": Governorate.HOMS,
                "interests": [Interest.HEALTH],
                "education": Education.PREFER_NOT_TO_SAY,
                "occupation": Occupation.PREFER_NOT_TO_SAY,
            },
            86,
        ),
        (
            {
                "age": 30,
                "gender": Gender.FEMALE,
                "region": Governorate.HOMS,
                "interests": [Interest.HEALTH],
                "education": Education.PREFER_NOT_TO_SAY,
                "occupation": Occupation.PREFER_NOT_TO_SAY,
                "marital_status": MaritalStatus.PREFER_NOT_TO_SAY,
            },
            100,
        ),
    ],
)
def test_completion_percent_counts_seven_details(values, percent):
    assert profile_with(**values).completion_percent() == percent


@pytest.mark.parametrize(
    ("values", "complete"),
    [
        (
            {
                "age": 30,
                "gender": Gender.MALE,
                "region": Governorate.DAMASCUS,
                "interests": [Interest.ARTS],
            },
            True,
        ),
        ({"age": 30, "gender": Gender.MALE, "region": Governorate.DAMASCUS}, False),
        ({"age": 30, "gender": Gender.MALE, "interests": [Interest.ARTS]}, False),
        (
            {
                "age": 30,
                "gender": Gender.MALE,
                "region": "Amman",
                "interests": [Interest.ARTS],
            },
            False,
        ),
    ],
)
def test_is_complete_needs_the_four_required_details(values, complete):
    assert profile_with(**values).is_complete() is complete


def test_options_return_the_five_lists_in_enum_order(profile_service):
    options = profile_service.options()

    assert list(options) == [
        "governorates",
        "education",
        "occupation",
        "marital_status",
        "interests",
    ]
    assert [item["code"] for item in options["governorates"]] == Governorate.values
    assert options["governorates"][-1] == {
        "code": "OUTSIDE_SYRIA",
        "label": "Outside Syria",
    }
    for key in ("education", "occupation", "marital_status"):
        assert options[key][-1]["code"] == "PREFER_NOT_TO_SAY"
    assert [item["code"] for item in options["interests"]] == Interest.values
