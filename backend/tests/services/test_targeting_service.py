import pytest

from apps.core.models import RespondentProfile, Survey, TargetingCriteria, User
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
        regions=["DAMASCUS"],
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
        regions=["DAMASCUS"],
    )

    initial = targeting_service.get_criteria_initial(provider, survey.survey_id)

    assert initial == {
        "gender": Gender.FEMALE,
        "age_min": 18,
        "age_max": 40,
        "regions": ["DAMASCUS"],
        "education_levels": [],
        "occupations": [],
        "marital_statuses": [],
        "interests": [],
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
        regions=["DAMASCUS"],
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
    targeting_service.save_criteria(provider, survey.survey_id, regions=["DAMASCUS"])

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


LIST_MESSAGES = {
    "regions": "Choose governorates from the list.",
    "education_levels": "Choose education levels from the list.",
    "occupations": "Choose occupations from the list.",
    "marital_statuses": "Choose marital statuses from the list.",
    "interests": "Choose interests from the list.",
}

VALID_LIST_VALUES = {
    "regions": ["OUTSIDE_SYRIA", "HOMS"],
    "education_levels": ["MASTER", "BASIC"],
    "occupations": ["RETIRED", "STUDENT"],
    "marital_statuses": ["WIDOWED", "SINGLE"],
    "interests": ["ARTS", "TECHNOLOGY"],
}


@pytest.mark.django_db
@pytest.mark.parametrize("field", list(LIST_MESSAGES))
@pytest.mark.parametrize("bad_value", ["Damascus", "damascus", " MASTER ", "AMMAN", "", None])
def test_save_criteria_rejects_values_outside_each_lists_enum(
    targeting_service, field, bad_value
):
    provider = create_user("provider-list-unknown@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError, match=LIST_MESSAGES[field]):
        targeting_service.save_criteria(
            provider, survey.survey_id, **{field: [VALID_LIST_VALUES[field][0], bad_value]}
        )

    assert TargetingRepository().find_by_survey_id(survey.survey_id) is None


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["education_levels", "occupations", "marital_statuses"])
def test_save_criteria_rejects_prefer_not_to_say(targeting_service, field):
    provider = create_user("provider-list-pnts@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError, match=LIST_MESSAGES[field]):
        targeting_service.save_criteria(
            provider, survey.survey_id, **{field: ["PREFER_NOT_TO_SAY"]}
        )


@pytest.mark.django_db
def test_save_criteria_drops_duplicates_keeping_first_order(targeting_service):
    provider = create_user("provider-list-dupes@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    doubled = {field: [a, b, a, b, a] for field, (a, b) in VALID_LIST_VALUES.items()}

    criteria = targeting_service.save_criteria(provider, survey.survey_id, **doubled)
    criteria.refresh_from_db()

    for field, values in VALID_LIST_VALUES.items():
        assert getattr(criteria, field) == values


@pytest.mark.django_db
def test_save_criteria_defaults_every_list_to_empty(targeting_service):
    provider = create_user("provider-list-empty@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    targeting_service.save_criteria(provider, survey.survey_id, regions=["HOMS"])

    criteria = targeting_service.save_criteria(provider, survey.survey_id)

    for field in LIST_MESSAGES:
        assert getattr(criteria, field) == []
    assert criteria.is_open_to_all()


@pytest.mark.django_db
def test_region_match_needs_equal_codes(targeting_service):
    provider = create_user("provider-region-equal@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-region-equal@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    create_profile(respondent, age=30, gender=Gender.FEMALE, region="RIF_DIMASHQ")
    targeting_service.save_criteria(provider, survey.survey_id, regions=["DAMASCUS"])

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id) is False

    targeting_service.save_criteria(provider, survey.survey_id, regions=["RIF_DIMASHQ"])

    assert targeting_service.match_respondent_to_survey(respondent, survey.survey_id) is True


# P-17 rule rows: one passing and one failing case per row, checked on unsaved objects.
def rule_profile(**values):
    return RespondentProfile(
        **{
            "age": 30,
            "gender": Gender.FEMALE,
            "region": "HOMS",
            "interests": ["SPORTS", "ARTS"],
            "education": "BACHELOR",
            "occupation": "STUDENT",
            "marital_status": "SINGLE",
            **values,
        }
    )


RULE_ROWS = [
    pytest.param({"gender": None}, {}, True, id="gender-unset-passes"),
    pytest.param({"gender": ""}, {}, True, id="gender-blank-passes"),
    pytest.param({"gender": Gender.ANY}, {}, True, id="gender-any-passes"),
    pytest.param({"gender": Gender.FEMALE}, {}, True, id="gender-equal-passes"),
    pytest.param({"gender": Gender.MALE}, {}, False, id="gender-other-fails"),
    pytest.param({"age_min": 30, "age_max": 30}, {}, True, id="age-bounds-inclusive-pass"),
    pytest.param({"age_min": 31}, {}, False, id="age-below-min-fails"),
    pytest.param({"age_max": 29}, {}, False, id="age-above-max-fails"),
    pytest.param({"regions": ["ALEPPO", "HOMS"]}, {}, True, id="region-in-list-passes"),
    pytest.param({"regions": ["ALEPPO"]}, {}, False, id="region-not-in-list-fails"),
    pytest.param({"education_levels": ["BACHELOR"]}, {}, True, id="education-in-list-passes"),
    pytest.param({"education_levels": ["MASTER"]}, {}, False, id="education-not-in-list-fails"),
    pytest.param({"occupations": ["RETIRED", "STUDENT"]}, {}, True, id="occupation-in-list-passes"),
    pytest.param({"occupations": ["RETIRED"]}, {}, False, id="occupation-not-in-list-fails"),
    pytest.param({"marital_statuses": ["SINGLE"]}, {}, True, id="marital-in-list-passes"),
    pytest.param({"marital_statuses": ["MARRIED"]}, {}, False, id="marital-not-in-list-fails"),
    pytest.param({"interests": ["ARTS", "HEALTH"]}, {}, True, id="interests-one-common-passes"),
    pytest.param({"interests": ["HEALTH", "FOOD"]}, {}, False, id="interests-none-common-fails"),
    pytest.param({}, {}, True, id="no-restriction-passes"),
    pytest.param(
        {"regions": ["HOMS"], "education_levels": ["MASTER"]}, {}, False, id="fields-combine-with-and"
    ),
]


@pytest.mark.parametrize(("criteria_values", "profile_values", "expected"), RULE_ROWS)
def test_profile_matches_criteria_rule_rows(
    targeting_service, criteria_values, profile_values, expected
):
    criteria = TargetingCriteria(**criteria_values)
    profile = rule_profile(**profile_values)

    assert targeting_service.profile_matches_criteria(criteria, profile) is expected


@pytest.mark.parametrize(
    ("list_name", "profile_field", "listed_value"),
    [
        ("education_levels", "education", "BACHELOR"),
        ("occupations", "occupation", "STUDENT"),
        ("marital_statuses", "marital_status", "SINGLE"),
    ],
)
@pytest.mark.parametrize("unshared", ["", "PREFER_NOT_TO_SAY"])
def test_unshared_detail_fails_a_non_empty_list_and_passes_an_empty_one(
    targeting_service, list_name, profile_field, listed_value, unshared
):
    profile = rule_profile(**{profile_field: unshared})

    assert not targeting_service.profile_matches_criteria(
        TargetingCriteria(**{list_name: [listed_value]}), profile
    )
    assert targeting_service.profile_matches_criteria(
        TargetingCriteria(**{list_name: []}), profile
    )
