import pytest

from apps.core.models import RespondentProfile, Survey, User
from core.enums import AccountStatus, Gender, UserType
from core.exceptions import NotEditable, UnauthorizedAction, ValidationError
from repositories.profile_repository import ProfileRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.targeting_service import TargetingService


@pytest.fixture
def targeting_service():
    return TargetingService()


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey(provider, title="Survey"):
    return SurveyRepository().save(
        Survey(provider=provider, title=title, description="Description")
    )


def publish_survey(survey):
    survey.publish()
    return SurveyRepository().update(survey)


def create_profile(user, age=30, gender=Gender.FEMALE, region="DAMASCUS"):
    return ProfileRepository().save(
        RespondentProfile(
            user=user,
            age=age,
            gender=gender,
            region=region,
            interests=["TECHNOLOGY"],
        )
    )


@pytest.mark.django_db
def test_provider_can_save_criteria_for_own_draft_survey(targeting_service):
    provider = create_user("provider-criteria@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    criteria = targeting_service.save_criteria(
        provider,
        survey.survey_id,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        region="DAMASCUS",
    )

    assert criteria.survey == survey
    assert criteria.gender == Gender.FEMALE


@pytest.mark.django_db
def test_non_service_provider_cannot_save_criteria(targeting_service):
    respondent = create_user("respondent-criteria@example.com", UserType.RESPONDENT)
    provider = create_user("provider-criteria-owner@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(UnauthorizedAction):
        targeting_service.save_criteria(respondent, survey.survey_id)


@pytest.mark.django_db
def test_provider_cannot_save_criteria_for_another_providers_survey(targeting_service):
    owner = create_user("owner-criteria@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user("other-criteria@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(owner)

    with pytest.raises(UnauthorizedAction):
        targeting_service.save_criteria(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_provider_cannot_update_criteria_for_published_survey(targeting_service):
    provider = create_user("provider-published-criteria@example.com", UserType.SERVICE_PROVIDER)
    survey = publish_survey(create_survey(provider))

    with pytest.raises(NotEditable):
        targeting_service.save_criteria(provider, survey.survey_id)


@pytest.mark.django_db
def test_invalid_age_range_is_rejected(targeting_service):
    provider = create_user("provider-age-range@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError):
        targeting_service.save_criteria(provider, survey.survey_id, age_min=50, age_max=20)


@pytest.mark.django_db
def test_negative_age_is_rejected(targeting_service):
    provider = create_user("provider-negative-age@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError):
        targeting_service.save_criteria(provider, survey.survey_id, age_min=-1)


@pytest.mark.django_db
def test_gender_any_is_accepted_for_targeting_criteria(targeting_service):
    provider = create_user("provider-any-gender@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    criteria = targeting_service.save_criteria(
        provider,
        survey.survey_id,
        gender=Gender.ANY,
    )

    assert criteria.gender == Gender.ANY


@pytest.mark.django_db
def test_get_criteria_initial_returns_existing_criteria_data(targeting_service):
    provider = create_user(
        "provider-criteria-initial@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    TargetingRepository().create_or_update(
        survey=survey,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        region="DAMASCUS",
    )

    initial = targeting_service.get_criteria_initial(provider, survey.survey_id)

    assert initial == {
        "gender": Gender.FEMALE,
        "age_min": 18,
        "age_max": 40,
        "region": "DAMASCUS",
    }


@pytest.mark.django_db
def test_get_criteria_initial_returns_empty_data_when_criteria_missing(
    targeting_service,
):
    provider = create_user(
        "provider-criteria-initial-empty@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)

    assert targeting_service.get_criteria_initial(provider, survey.survey_id) == {}


@pytest.mark.django_db
def test_non_owner_cannot_get_criteria_initial_data(targeting_service):
    owner = create_user(
        "owner-criteria-initial@example.com",
        UserType.SERVICE_PROVIDER,
    )
    other_provider = create_user(
        "other-criteria-initial@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(owner)

    with pytest.raises(UnauthorizedAction):
        targeting_service.get_criteria_initial(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_non_service_provider_cannot_get_criteria_initial_data(targeting_service):
    respondent = create_user(
        "respondent-criteria-initial@example.com",
        UserType.RESPONDENT,
    )
    provider = create_user(
        "provider-criteria-initial-owner@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)

    with pytest.raises(UnauthorizedAction):
        targeting_service.get_criteria_initial(respondent, survey.survey_id)


@pytest.mark.django_db
def test_exact_respondent_match_returns_true(targeting_service):
    provider = create_user("provider-exact@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-exact@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=30, gender=Gender.FEMALE, region="DAMASCUS")
    targeting_service.save_criteria(
        provider,
        survey.survey_id,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        region="DAMASCUS",
    )

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
def test_gender_any_matches_any_respondent_gender(targeting_service):
    provider = create_user("provider-any-match@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-any-match@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=30, gender=Gender.MALE, region="DAMASCUS")
    targeting_service.save_criteria(provider, survey.survey_id, gender=Gender.ANY)

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
def test_age_mismatch_returns_false(targeting_service):
    provider = create_user("provider-age-mismatch@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-age-mismatch@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=17, gender=Gender.FEMALE, region="DAMASCUS")
    targeting_service.save_criteria(provider, survey.survey_id, age_min=18, age_max=40)

    assert not targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
def test_region_mismatch_returns_false(targeting_service):
    provider = create_user("provider-region-mismatch@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-region-mismatch@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=30, gender=Gender.FEMALE, region="ALEPPO")
    targeting_service.save_criteria(provider, survey.survey_id, region="DAMASCUS")

    assert not targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
def test_respondent_without_profile_returns_false(targeting_service):
    provider = create_user("provider-no-profile@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-no-profile@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    targeting_service.save_criteria(provider, survey.survey_id, gender=Gender.ANY)

    assert not targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
def test_incomplete_respondent_profile_returns_false(targeting_service):
    provider = create_user("provider-incomplete@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-incomplete@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="",
            interests=["TECHNOLOGY"],
        )
    )
    targeting_service.save_criteria(provider, survey.survey_id, gender=Gender.ANY)

    assert not targeting_service.match_respondent_to_survey(respondent, survey.survey_id)


@pytest.mark.django_db
@pytest.mark.parametrize("region", ["Damascus", "damascus", " DAMASCUS ", "AMMAN", ""])
def test_save_criteria_rejects_unknown_or_padded_governorate(targeting_service, region):
    provider = create_user("provider-region-unknown@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError, match="Choose a governorate from the list."):
        targeting_service.save_criteria(provider, survey.survey_id, region=region)

    assert TargetingRepository().find_by_survey_id(survey.survey_id) is None


@pytest.mark.django_db
def test_save_criteria_accepts_a_governorate_code_or_none(targeting_service):
    provider = create_user("provider-region-code@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    criteria = targeting_service.save_criteria(
        provider, survey.survey_id, region="OUTSIDE_SYRIA"
    )
    assert criteria.region == "OUTSIDE_SYRIA"

    criteria = targeting_service.save_criteria(provider, survey.survey_id, region=None)
    assert criteria.region is None


@pytest.mark.django_db
def test_region_match_needs_equal_codes(targeting_service):
    provider = create_user("provider-region-equal@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-region-equal@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=30, gender=Gender.FEMALE, region="RIF_DIMASHQ")
    targeting_service.save_criteria(provider, survey.survey_id, region="DAMASCUS")

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id) is False

    targeting_service.save_criteria(provider, survey.survey_id, region="RIF_DIMASHQ")

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id) is True
