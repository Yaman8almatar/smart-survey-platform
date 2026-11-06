import pytest

from apps.core.models import Question, QuestionOption, RespondentProfile, Response, User
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
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


def add_targeting(survey, gender=Gender.ANY, age_min=None, age_max=None, region=None):
    return TargetingRepository().create_or_update(
        survey=survey,
        gender=gender,
        age_min=age_min,
        age_max=age_max,
        region=region,
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
            region="Damascus",
            interests="Technology",
        )
    )

    eligible = survey_service.create_survey(provider, "Eligible", "Description")
    add_question(eligible)
    add_targeting(
        eligible,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=40,
        region="Damascus",
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
        region="Damascus",
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
        region="Damascus",
    )

    surveys = survey_service.get_eligible_surveys(respondent)

    assert [survey.survey_id for survey in surveys] == [eligible.survey_id]


@pytest.mark.django_db
def test_eligible_surveys_match_region_ignoring_case_and_spaces(survey_service):
    provider = create_user("provider-eligible-region@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-eligible-region@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region=" damascus ",
            interests="Technology",
        )
    )
    survey = survey_service.create_survey(provider, "Regional", "Description")
    add_question(survey)
    add_targeting(survey, region="Damascus")
    survey_service.publish_survey(provider, survey.survey_id)

    surveys = survey_service.get_eligible_surveys(respondent)

    assert [eligible.survey_id for eligible in surveys] == [survey.survey_id]


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
def test_eligible_survey_items_include_question_count_for_eligible_surveys_only(
    survey_service,
):
    provider = create_user("provider-items@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-items@example.com", UserType.RESPONDENT)
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
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


def respondent_with_profile(email, age=30, gender=Gender.FEMALE, region="Damascus"):
    respondent = create_user(email, UserType.RESPONDENT)
    profile = ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=age,
            gender=gender,
            region=region,
            interests="Technology",
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
def test_eligible_surveys_include_age_bounds(survey_service, targeting, age, eligible):
    provider = create_user("provider-age-bound@example.com", UserType.SERVICE_PROVIDER)
    respondent, _ = respondent_with_profile("respondent-age-bound@example.com", age=age)
    survey = published_survey_with_targeting(survey_service, provider, **targeting)

    surveys = survey_service.get_eligible_surveys(respondent)

    assert (survey in surveys) is eligible


@pytest.mark.django_db
@pytest.mark.parametrize("gender", [Gender.MALE, Gender.FEMALE])
def test_eligible_surveys_with_gender_any_include_every_gender(survey_service, gender):
    provider = create_user("provider-gender-any@example.com", UserType.SERVICE_PROVIDER)
    respondent, _ = respondent_with_profile("respondent-gender-any@example.com", gender=gender)
    survey = published_survey_with_targeting(survey_service, provider, gender=Gender.ANY)

    surveys = survey_service.get_eligible_surveys(respondent)

    assert [eligible.survey_id for eligible in surveys] == [survey.survey_id]


REGION_PAIRS = [
    pytest.param("Amman", " amman ", id="spaces-and-case"),
    pytest.param("AMMAN", "amman", id="upper-and-lower"),
    pytest.param("", "Amman", id="blank-criteria-region"),
    pytest.param("Amman", "Zarqa", id="different-region"),
    pytest.param(
        "Amman\t",
        "Amman",
        id="trailing-tab",
        marks=pytest.mark.xfail(strict=True, reason="DB TRIM keeps tabs; Python strip removes them"),
    ),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("criteria_region", "profile_region"), REGION_PAIRS)
def test_database_and_python_targeting_rules_agree(
    survey_service, criteria_region, profile_region
):
    provider = create_user("provider-agree@example.com", UserType.SERVICE_PROVIDER)
    respondent, profile = respondent_with_profile(
        "respondent-agree@example.com", region=profile_region
    )
    survey = published_survey_with_targeting(survey_service, provider, region=criteria_region)
    criteria = TargetingRepository().find_by_survey_id(survey.survey_id)

    matched_by_query = survey in SurveyRepository().find_eligible_for_respondent(
        profile, respondent.user_id
    )
    matched_by_service = TargetingService().profile_matches_criteria(criteria, profile)

    assert matched_by_query == matched_by_service


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
