import pytest

from apps.core.models import Question, RespondentProfile, Response, User
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
        "can_delete": False,
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
