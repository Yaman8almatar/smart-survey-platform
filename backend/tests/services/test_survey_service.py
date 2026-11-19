import random

import pytest
from django.utils import timezone

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import (
    AccountStatus,
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    QuestionType,
    SurveyStatus,
    UserType,
)
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    TargetingCriteriaNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.survey_service import SurveyService
from services.targeting_service import TargetingService


@pytest.fixture
def survey_service():
    return SurveyService()


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def add_question(survey):
    return QuestionRepository().save(
        Question(
            survey=survey,
            question_text="How was the service?",
            question_type=QuestionType.OPEN_TEXT,
            is_required=True,
            order_index=1,
        )
    )


def add_targeting(survey, gender=Gender.ANY, age_min=None, age_max=None, **lists):
    return TargetingRepository().create_or_update(
        survey=survey,
        gender=gender,
        age_min=age_min,
        age_max=age_max,
        **lists,
    )


def action_flags(item):
    return {
        "can_edit": item["can_edit"],
        "can_delete": item["can_delete"],
        "can_publish": item["can_publish"],
        "can_close": item["can_close"],
        "can_manage_questions": item["can_manage_questions"],
        "can_manage_targeting": item["can_manage_targeting"],
        "can_view_analytics": item["can_view_analytics"],
    }


@pytest.mark.django_db
def test_service_provider_can_create_survey(survey_service):
    provider = create_user("provider-create@example.com", UserType.SERVICE_PROVIDER)

    survey = survey_service.create_survey(provider, "Customer Survey", "Feedback")

    assert survey.provider == provider
    assert survey.title == "Customer Survey"
    assert survey.status == SurveyStatus.DRAFT


@pytest.mark.django_db
def test_non_service_provider_cannot_create_survey(survey_service):
    respondent = create_user("respondent-create@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        survey_service.create_survey(respondent, "Customer Survey", "Feedback")


@pytest.mark.django_db
def test_provider_can_update_own_draft_survey(survey_service):
    provider = create_user("provider-update@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Old Title", "Old Description")

    updated = survey_service.update_survey(
        provider,
        survey.survey_id,
        "New Title",
        "New Description",
    )

    assert updated.title == "New Title"
    assert updated.description == "New Description"


@pytest.mark.django_db
@pytest.mark.parametrize("title", ["", "   ", None])
def test_blank_title_is_rejected_on_create(survey_service, title):
    provider = create_user("provider-blank-create@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(ValidationError):
        survey_service.create_survey(provider, title, "Description")

    assert not SurveyRepository().find_by_provider_id(provider.user_id).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("title", ["", "   ", None])
def test_blank_title_is_rejected_on_update(survey_service, title):
    provider = create_user("provider-blank-update@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Old Title", "Old Description")

    with pytest.raises(ValidationError):
        survey_service.update_survey(provider, survey.survey_id, title, "New Description")

    assert SurveyRepository().find_by_id(survey.survey_id).title == "Old Title"


@pytest.mark.django_db
def test_provider_cannot_update_published_survey(survey_service):
    provider = create_user(
        "provider-update-published@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    survey_service.publish_survey(provider, survey.survey_id)

    with pytest.raises(NotEditable):
        survey_service.update_survey(provider, survey.survey_id, "Title", "Description")


@pytest.mark.django_db
def test_provider_cannot_update_another_providers_survey(survey_service):
    owner = create_user("owner-update@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user("other-update@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(owner, "Survey", "Description")

    with pytest.raises(UnauthorizedAction):
        survey_service.update_survey(
            other_provider,
            survey.survey_id,
            "New Title",
            "New Description",
        )


@pytest.mark.django_db
def test_provider_can_get_own_survey(survey_service):
    provider = create_user("provider-get-own@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")

    result = survey_service.get_provider_survey(provider, survey.survey_id)

    assert result == survey


@pytest.mark.django_db
def test_provider_cannot_get_another_providers_survey(survey_service):
    owner = create_user("owner-get@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user("other-get@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(owner, "Survey", "Description")

    with pytest.raises(UnauthorizedAction):
        survey_service.get_provider_survey(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_non_service_provider_cannot_get_provider_survey(survey_service):
    respondent = create_user("respondent-get-survey@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        survey_service.get_provider_survey(respondent, 1)


@pytest.mark.django_db
def test_missing_provider_survey_is_rejected(survey_service):
    provider = create_user("provider-missing-get@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(SurveyNotFound):
        survey_service.get_provider_survey(provider, 999999)


@pytest.mark.django_db
def test_provider_can_delete_own_draft_survey(survey_service):
    provider = create_user("provider-delete@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")

    survey_service.delete_survey(provider, survey.survey_id)

    assert SurveyRepository().find_by_id(survey.survey_id) is None


@pytest.mark.django_db
def test_provider_can_delete_own_closed_survey(survey_service):
    provider = create_user("provider-delete-closed@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    survey_service.publish_survey(provider, survey.survey_id)
    survey_service.close_survey(provider, survey.survey_id)

    survey_service.delete_survey(provider, survey.survey_id)

    assert SurveyRepository().find_by_id(survey.survey_id) is None


@pytest.mark.django_db
def test_provider_cannot_delete_published_survey(survey_service):
    provider = create_user(
        "provider-delete-published@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    survey_service.publish_survey(provider, survey.survey_id)

    with pytest.raises(NotEditable):
        survey_service.delete_survey(provider, survey.survey_id)


@pytest.mark.django_db
def test_provider_cannot_delete_another_providers_survey(survey_service):
    owner = create_user("owner-delete@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user("other-delete@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(owner, "Survey", "Description")

    with pytest.raises(UnauthorizedAction):
        survey_service.delete_survey(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_publish_survey_requires_at_least_one_question(survey_service):
    provider = create_user("provider-question@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_targeting(survey)

    with pytest.raises(ValidationError):
        survey_service.publish_survey(provider, survey.survey_id)


@pytest.mark.django_db
def test_publish_survey_requires_targeting_criteria(survey_service):
    provider = create_user("provider-targeting@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)

    with pytest.raises(TargetingCriteriaNotFound):
        survey_service.publish_survey(provider, survey.survey_id)


@pytest.mark.django_db
def test_publish_survey_changes_status_to_published(survey_service):
    provider = create_user("provider-publish@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)
    add_targeting(survey)

    published = survey_service.publish_survey(provider, survey.survey_id)

    assert published.status == SurveyStatus.PUBLISHED
    assert published.published_at is not None


@pytest.mark.django_db
def test_close_survey_changes_status_to_closed(survey_service):
    provider = create_user("provider-close@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    published = survey_service.publish_survey(provider, survey.survey_id)

    closed = survey_service.close_survey(provider, published.survey_id)

    assert closed.status == SurveyStatus.CLOSED
    assert closed.closed_at is not None


@pytest.mark.django_db
def test_draft_survey_action_flags_are_correct(survey_service):
    provider = create_user("provider-draft-actions@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Draft Survey", "Description")

    items = survey_service.list_provider_survey_items(provider)

    assert items[0]["survey"] == survey
    assert action_flags(items[0]) == {
        "can_edit": True,
        "can_delete": True,
        "can_publish": True,
        "can_close": False,
        "can_manage_questions": True,
        "can_manage_targeting": True,
        "can_view_analytics": False,
    }


@pytest.mark.django_db
def test_published_survey_action_flags_are_correct(survey_service):
    provider = create_user(
        "provider-published-actions@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = survey_service.create_survey(provider, "Published Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    survey_service.publish_survey(provider, survey.survey_id)

    items = survey_service.list_provider_survey_items(provider)

    assert action_flags(items[0]) == {
        "can_edit": False,
        "can_delete": False,
        "can_publish": False,
        "can_close": True,
        "can_manage_questions": False,
        "can_manage_targeting": False,
        "can_view_analytics": True,
    }


@pytest.mark.django_db
def test_closed_survey_action_flags_are_correct(survey_service):
    provider = create_user("provider-closed-actions@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Closed Survey", "Description")
    add_question(survey)
    add_targeting(survey)
    survey_service.publish_survey(provider, survey.survey_id)
    survey_service.close_survey(provider, survey.survey_id)

    items = survey_service.list_provider_survey_items(provider)

    assert action_flags(items[0]) == {
        "can_edit": False,
        "can_delete": True,
        "can_publish": False,
        "can_close": False,
        "can_manage_questions": False,
        "can_manage_targeting": False,
        "can_view_analytics": True,
    }


@pytest.mark.django_db
def test_non_service_provider_cannot_get_provider_survey_items(survey_service):
    respondent = create_user("respondent-actions@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        survey_service.list_provider_survey_items(respondent)


@pytest.mark.django_db
def test_respondent_gets_only_eligible_published_unanswered_surveys(survey_service):
    provider = create_user("provider-eligible@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-eligible@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="DAMASCUS",
            interests=["TECHNOLOGY"],
        )
    )

    eligible = survey_service.create_survey(provider, "Eligible", "Description")
    add_question(eligible)
    add_targeting(
        eligible,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        regions=["DAMASCUS"],
    )
    survey_service.publish_survey(provider, eligible.survey_id)

    wrong_target = survey_service.create_survey(provider, "Wrong Target", "Description")
    add_question(wrong_target)
    add_targeting(wrong_target, gender=Gender.MALE, age_min=18, age_max=40)
    survey_service.publish_survey(provider, wrong_target.survey_id)

    answered = survey_service.create_survey(provider, "Answered", "Description")
    add_question(answered)
    add_targeting(
        answered,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        regions=["DAMASCUS"],
    )
    survey_service.publish_survey(provider, answered.survey_id)
    ResponseRepository().save(Response(survey=answered, respondent=respondent))

    draft = survey_service.create_survey(provider, "Draft", "Description")
    add_question(draft)
    add_targeting(
        draft,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        regions=["DAMASCUS"],
    )

    surveys = eligible_list(survey_service, respondent)

    assert [survey.survey_id for survey in surveys] == [eligible.survey_id]


@pytest.mark.django_db
def test_eligible_list_matches_equal_governorate_codes_only(survey_service):
    provider = create_user("provider-eligible-region@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-eligible-region@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="DAMASCUS",
            interests=["TECHNOLOGY"],
        )
    )
    matching = survey_service.create_survey(provider, "Damascus", "Description")
    add_question(matching)
    add_targeting(matching, regions=["DAMASCUS"])
    survey_service.publish_survey(provider, matching.survey_id)
    other = survey_service.create_survey(provider, "Rif Dimashq", "Description")
    add_question(other)
    add_targeting(other, regions=["RIF_DIMASHQ"])
    survey_service.publish_survey(provider, other.survey_id)

    surveys = eligible_list(survey_service, respondent)

    assert [eligible.survey_id for eligible in surveys] == [matching.survey_id]


def eligible_list(survey_service, respondent):
    return [item["survey"] for item in survey_service.get_eligible_survey_items(respondent)]


def add_choice_question(survey, option_count):
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Would you recommend us?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            is_required=True,
            order_index=2,
        )
    )
    for index in range(option_count):
        QuestionRepository().save_option(
            QuestionOption(question=question, option_text=f"Option {index}", order_index=index)
        )
    return question


@pytest.mark.django_db
@pytest.mark.parametrize("option_count", [0, 1])
def test_publish_survey_rejects_multiple_choice_question_with_fewer_than_two_options(
    survey_service,
    option_count,
):
    provider = create_user(
        f"provider-choice-publish-{option_count}@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = survey_service.create_survey(provider, "Choice", "Description")
    add_choice_question(survey, option_count)
    add_targeting(survey)

    with pytest.raises(ValidationError):
        survey_service.publish_survey(provider, survey.survey_id)

    assert SurveyRepository().find_by_id(survey.survey_id).status == SurveyStatus.DRAFT


@pytest.mark.django_db
def test_publish_survey_accepts_multiple_choice_question_with_two_options(survey_service):
    provider = create_user("provider-choice-publish-ok@example.com", UserType.SERVICE_PROVIDER)
    survey = survey_service.create_survey(provider, "Choice", "Description")
    add_choice_question(survey, 2)
    add_targeting(survey)

    published = survey_service.publish_survey(provider, survey.survey_id)

    assert published.status == SurveyStatus.PUBLISHED


@pytest.mark.django_db
def test_eligible_survey_items_include_question_count_for_eligible_only(
    survey_service,
):
    provider = create_user("provider-items@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-items@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="DAMASCUS",
            interests=["TECHNOLOGY"],
        )
    )

    eligible = survey_service.create_survey(provider, "Eligible", "Description")
    add_question(eligible)
    QuestionRepository().save(
        Question(
            survey=eligible,
            question_text="Second question",
            question_type=QuestionType.OPEN_TEXT,
            is_required=False,
            order_index=2,
        )
    )
    add_targeting(eligible, gender=Gender.FEMALE)
    survey_service.publish_survey(provider, eligible.survey_id)

    wrong_target = survey_service.create_survey(provider, "Wrong Target", "Description")
    add_question(wrong_target)
    add_targeting(wrong_target, gender=Gender.MALE)
    survey_service.publish_survey(provider, wrong_target.survey_id)

    items = survey_service.get_eligible_survey_items(respondent)

    assert [(item["survey"].survey_id, item["question_count"]) for item in items] == [
        (eligible.survey_id, 2)
    ]


@pytest.mark.django_db
def test_non_respondent_cannot_get_eligible_survey_items(survey_service):
    provider = create_user("provider-items-denied@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        survey_service.get_eligible_survey_items(provider)


def published_survey_with_targeting(survey_service, provider, **targeting):
    survey = survey_service.create_survey(provider, "Targeted", "Description")
    add_question(survey)
    add_targeting(survey, **targeting)
    return survey_service.publish_survey(provider, survey.survey_id)


def respondent_with_profile(email, age=30, gender=Gender.FEMALE, region="DAMASCUS"):
    respondent = create_user(email, UserType.RESPONDENT)
    profile = ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=age,
            gender=gender,
            region=region,
            interests=["TECHNOLOGY"],
        )
    )
    return respondent, profile


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("targeting", "age", "eligible"),
    [
        ({"age_min": 18}, 17, False),
        ({"age_min": 18}, 18, True),
        ({"age_min": 18}, 19, True),
        ({"age_max": 35}, 34, True),
        ({"age_max": 35}, 35, True),
        ({"age_max": 35}, 36, False),
    ],
)
def test_eligible_list_includes_age_bounds(survey_service, targeting, age, eligible):
    provider = create_user("provider-age-bound@example.com", UserType.SERVICE_PROVIDER)
    respondent, _ = respondent_with_profile("respondent-age-bound@example.com", age=age)
    survey = published_survey_with_targeting(survey_service, provider, **targeting)

    surveys = eligible_list(survey_service, respondent)

    assert (survey in surveys) is eligible


@pytest.mark.django_db
@pytest.mark.parametrize("gender", [Gender.MALE, Gender.FEMALE])
def test_eligible_list_with_gender_any_includes_every_gender(survey_service, gender):
    provider = create_user("provider-gender-any@example.com", UserType.SERVICE_PROVIDER)
    respondent, _ = respondent_with_profile("respondent-gender-any@example.com", gender=gender)
    survey = published_survey_with_targeting(survey_service, provider, gender=Gender.ANY)

    surveys = eligible_list(survey_service, respondent)

    assert [eligible.survey_id for eligible in surveys] == [survey.survey_id]


def without_prefer_not_to_say(enum):
    return [value for value in enum.values if value != "PREFER_NOT_TO_SAY"]


def random_list(rng, values):
    """Empty half the time, otherwise one to four distinct values."""
    if rng.random() < 0.5:
        return []
    return rng.sample(values, rng.randint(1, 4))


def random_detail(rng, enum):
    """An optional profile detail: "" a quarter, PREFER_NOT_TO_SAY an eighth, else a value."""
    draw = rng.random()
    if draw < 0.25:
        return ""
    if draw < 0.375:
        return "PREFER_NOT_TO_SAY"
    return rng.choice(without_prefer_not_to_say(enum))


def add_excluded_profiles(sources):
    """Five profiles the reach count must never include, each copying a pool profile."""
    provider = create_user("provider-excluded@example.com", UserType.SERVICE_PROVIDER)
    cases = [
        ({"account_status": AccountStatus.SUSPENDED}, {}),
        ({"is_active": False}, {}),
        ({}, {"interests": []}),
        ({}, {"region": ""}),
        (None, {}),
    ]
    excluded = []
    for index, ((user_changes, profile_changes), source) in enumerate(zip(cases, sources)):
        if user_changes is None:
            user = provider
        else:
            user = User.objects.create(
                email=f"respondent-excluded-{index}@example.com",
                name="Excluded",
                user_type=UserType.RESPONDENT,
                **user_changes,
            )
        values = {
            "age": source.age,
            "gender": source.gender,
            "region": source.region,
            "interests": list(source.interests),
            "education": source.education,
            "occupation": source.occupation,
            "marital_status": source.marital_status,
            **profile_changes,
        }
        excluded.append(RespondentProfile.objects.create(user=user, **values))
    return excluded


@pytest.mark.django_db
def test_query_and_python_rule_agree_on_random_profiles_and_criteria():
    """P-18: the three forms of the P-17 rule agree.

    The survey query and the Python rule pick the same surveys for each profile, and the
    reach count of each criteria is the number of pool profiles the Python rule accepts.
    """
    rng = random.Random(20261118)
    provider = create_user("provider-parity@example.com", UserType.SERVICE_PROVIDER)

    for index in range(50):
        survey = Survey.objects.create(
            provider=provider,
            title=f"Parity {index}",
            status=SurveyStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        age_min = None if rng.random() < 0.5 else rng.randint(18, 50)
        age_max = None if rng.random() < 0.5 else rng.randint(age_min or 18, 70)
        TargetingCriteria.objects.create(
            survey=survey,
            gender=rng.choice([None, Gender.ANY, Gender.MALE, Gender.FEMALE]),
            age_min=age_min,
            age_max=age_max,
            regions=random_list(rng, Governorate.values),
            education_levels=random_list(rng, without_prefer_not_to_say(Education)),
            occupations=random_list(rng, without_prefer_not_to_say(Occupation)),
            marital_statuses=random_list(rng, without_prefer_not_to_say(MaritalStatus)),
            interests=random_list(rng, Interest.values),
        )

    profiles = []
    for index in range(200):
        user = User.objects.create(
            email=f"respondent-parity-{index}@example.com",
            name="Parity",
            user_type=UserType.RESPONDENT,
        )
        profile = RespondentProfile.objects.create(
            user=user,
            age=rng.randint(16, 75),
            gender=rng.choice([Gender.MALE, Gender.FEMALE]),
            region=rng.choice(Governorate.values),
            interests=rng.sample(Interest.values, rng.randint(1, 4)),
            education=random_detail(rng, Education),
            occupation=random_detail(rng, Occupation),
            marital_status=random_detail(rng, MaritalStatus),
        )
        assert profile.is_complete()
        profiles.append(profile)

    excluded = add_excluded_profiles(profiles[:5])

    all_criteria = list(TargetingCriteria.objects.all())
    targeting_service = TargetingService()
    survey_repository = SurveyRepository()
    profile_repository = ProfileRepository()
    matched_pairs = 0
    python_counts = {criteria.survey_id: 0 for criteria in all_criteria}
    for profile in profiles:
        by_query = {
            survey.survey_id
            for survey in survey_repository.find_eligible_for_respondent(
                profile, profile.user_id
            )
        }
        by_python = {
            criteria.survey_id
            for criteria in all_criteria
            if targeting_service.profile_matches_criteria(criteria, profile)
        }
        assert by_query == by_python, f"profile {profile.profile_id} disagrees"
        matched_pairs += len(by_python)
        for survey_id in by_python:
            python_counts[survey_id] += 1

    share = matched_pairs / (len(profiles) * len(all_criteria))
    # The bound stops a rule that matches nothing or everything from passing.
    assert 0.05 <= share <= 0.95, f"matched share {share:.3f}"

    # Third form: the count query counts exactly the pool profiles the Python rule accepts,
    # so the five excluded profiles change no count.
    for criteria in all_criteria:
        assert profile_repository.count_matching(criteria) == python_counts[
            criteria.survey_id
        ], f"criteria of survey {criteria.survey_id} disagrees"
    assert profile_repository.count_pool() == len(profiles)
    assert profile_repository.count_matching(TargetingCriteria()) == len(profiles)
    # The exclusion is tested only if the Python rule alone would have counted them.
    assert any(
        targeting_service.profile_matches_criteria(criteria, profile)
        for criteria in all_criteria
        for profile in excluded
    )


@pytest.mark.django_db
def test_eligible_survey_items_use_a_fixed_number_of_queries(
    survey_service, django_assert_max_num_queries
):
    provider = create_user("provider-items-queries@example.com", UserType.SERVICE_PROVIDER)
    respondent, _ = respondent_with_profile("respondent-items-queries@example.com")
    for _ in range(5):
        published_survey_with_targeting(survey_service, provider, gender=Gender.FEMALE)

    with django_assert_max_num_queries(3):
        items = survey_service.get_eligible_survey_items(respondent)
        question_counts = [item["question_count"] for item in items]

    assert question_counts == [1] * 5


def seed_respondents():
    """Twelve complete profiles: genders and governorates mixed, one suspended account."""
    respondents = []
    for index, (gender, region) in enumerate(
        [(Gender.FEMALE, "DAMASCUS")] * 4
        + [(Gender.FEMALE, "HOMS")] * 3
        + [(Gender.MALE, "DAMASCUS")] * 3
        + [(Gender.FEMALE, "LATAKIA")] * 2
    ):
        respondent, _ = respondent_with_profile(
            f"respondent-reach-{index}@example.com", gender=gender, region=region
        )
        respondents.append(respondent)
    suspended = respondents[0]
    suspended.suspend()
    suspended.save()
    return respondents[1:]


@pytest.mark.django_db
def test_publish_stores_the_reach_that_matches_the_eligible_lists(survey_service):
    provider = create_user("provider-reach-publish@example.com", UserType.SERVICE_PROVIDER)
    active_respondents = seed_respondents()

    survey = published_survey_with_targeting(
        survey_service,
        provider,
        gender=Gender.FEMALE,
        regions=["DAMASCUS", "HOMS"],
    )

    seeing = [
        respondent
        for respondent in active_respondents
        if survey in eligible_list(survey_service, respondent)
    ]
    survey.refresh_from_db()
    assert survey.reach_at_publish == len(seeing) == 6


@pytest.mark.django_db
def test_publish_preview_returns_reach_criteria_and_question_count(survey_service):
    provider = create_user("provider-preview@example.com", UserType.SERVICE_PROVIDER)
    seed_respondents()
    survey = survey_service.create_survey(provider, "Preview", "Description")
    add_question(survey)
    add_question(survey)
    add_targeting(survey, gender=Gender.FEMALE, regions=["DAMASCUS", "HOMS"])

    preview = survey_service.get_publish_preview(provider, survey.survey_id)

    assert preview["reach"] == {"state": "narrowed", "count": 6, "total": 11, "percent": 55}
    assert preview["criteria"]["gender"] == Gender.FEMALE
    assert preview["criteria"]["regions"] == ["DAMASCUS", "HOMS"]
    assert preview["question_count"] == 2
    survey.refresh_from_db()
    assert survey.status == SurveyStatus.DRAFT


@pytest.mark.django_db
def test_publish_preview_raises_the_publish_errors(survey_service):
    provider = create_user("provider-preview-errors@example.com", UserType.SERVICE_PROVIDER)

    no_question = survey_service.create_survey(provider, "No question", "Description")
    add_targeting(no_question)
    with pytest.raises(ValidationError, match="at least one question"):
        survey_service.get_publish_preview(provider, no_question.survey_id)

    one_option = survey_service.create_survey(provider, "One option", "Description")
    add_choice_question(one_option, option_count=1)
    add_targeting(one_option)
    with pytest.raises(ValidationError, match="at least two options"):
        survey_service.get_publish_preview(provider, one_option.survey_id)

    no_criteria = survey_service.create_survey(provider, "No criteria", "Description")
    add_question(no_criteria)
    with pytest.raises(TargetingCriteriaNotFound):
        survey_service.get_publish_preview(provider, no_criteria.survey_id)


@pytest.mark.django_db
def test_publish_preview_needs_an_owned_draft(survey_service):
    provider = create_user("provider-preview-owner@example.com", UserType.SERVICE_PROVIDER)
    other = create_user("provider-preview-other@example.com", UserType.SERVICE_PROVIDER)
    survey = published_survey_with_targeting(survey_service, provider)

    with pytest.raises(NotEditable):
        survey_service.get_publish_preview(provider, survey.survey_id)
    with pytest.raises(UnauthorizedAction):
        survey_service.get_publish_preview(other, survey.survey_id)
