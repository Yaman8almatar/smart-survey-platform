import pytest

from apps.core.models import QuestionOption, RespondentProfile, Survey, User
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.question_repository import QuestionRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.question_service import QuestionService


@pytest.fixture
def question_service():
    return QuestionService()


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


def make_survey_answerable(survey, target_gender=Gender.ANY):
    TargetingRepository().create_or_update(survey=survey, gender=target_gender)
    publish_survey(survey)
    respondent = create_user(
        f"respondent-form-{survey.survey_id}@example.com",
        UserType.RESPONDENT,
    )
    ProfileRepository().save(
        RespondentProfile(
            user=respondent,
            age=30,
            gender=Gender.FEMALE,
            region="Damascus",
            interests="Technology",
        )
    )
    return respondent


def close_survey(survey):
    survey.close()
    return SurveyRepository().update(survey)


def add_question(
    service,
    provider,
    survey,
    question_type=QuestionType.OPEN_TEXT,
    text="How was the service?",
    order_index=0,
):
    return service.add_question(
        provider,
        survey.survey_id,
        text,
        question_type,
        True,
        order_index,
    )


@pytest.mark.django_db
def test_provider_can_add_question_to_own_draft_survey(question_service):
    provider = create_user("provider-question@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    question = add_question(question_service, provider, survey)

    assert question.survey == survey
    assert question.question_text == "How was the service?"


@pytest.mark.django_db
def test_non_service_provider_cannot_add_question(question_service):
    respondent = create_user("respondent-question@example.com", UserType.RESPONDENT)
    provider = create_user("provider-owner@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(UnauthorizedAction):
        add_question(question_service, respondent, survey)


@pytest.mark.django_db
def test_provider_cannot_add_question_to_another_providers_survey(question_service):
    owner = create_user("owner-question@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user("other-question@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(owner)

    with pytest.raises(UnauthorizedAction):
        add_question(question_service, other_provider, survey)


@pytest.mark.django_db
def test_provider_cannot_add_question_to_published_survey(question_service):
    provider = create_user("provider-published@example.com", UserType.SERVICE_PROVIDER)
    survey = publish_survey(create_survey(provider))

    with pytest.raises(NotEditable):
        add_question(question_service, provider, survey)


@pytest.mark.django_db
def test_empty_question_text_is_rejected(question_service):
    provider = create_user("provider-empty@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError):
        question_service.add_question(
            provider,
            survey.survey_id,
            " ",
            QuestionType.OPEN_TEXT,
            True,
            0,
        )


@pytest.mark.django_db
def test_negative_order_index_is_rejected(question_service):
    provider = create_user("provider-negative@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)

    with pytest.raises(ValidationError):
        question_service.add_question(
            provider,
            survey.survey_id,
            "How was the service?",
            QuestionType.OPEN_TEXT,
            True,
            -1,
        )


@pytest.mark.django_db
def test_provider_can_add_options_to_multiple_choice_question(question_service):
    provider = create_user("provider-options@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey, QuestionType.MULTIPLE_CHOICE)

    options = question_service.add_question_options(
        provider,
        question.question_id,
        ["Good", "Average", "Poor"],
    )

    assert [option.option_text for option in options] == ["Good", "Average", "Poor"]


@pytest.mark.django_db
def test_empty_option_list_is_rejected(question_service):
    provider = create_user("provider-empty-options@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey, QuestionType.MULTIPLE_CHOICE)

    with pytest.raises(ValidationError):
        question_service.add_question_options(provider, question.question_id, [])


@pytest.mark.django_db
def test_blank_option_text_is_rejected(question_service):
    provider = create_user("provider-blank-option@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey, QuestionType.MULTIPLE_CHOICE)

    with pytest.raises(ValidationError):
        question_service.add_question_options(provider, question.question_id, ["Good", " "])


@pytest.mark.django_db
def test_options_are_rejected_for_open_text_question(question_service):
    provider = create_user("provider-open-options@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey, QuestionType.OPEN_TEXT)

    with pytest.raises(ValidationError):
        question_service.add_question_options(provider, question.question_id, ["Good"])


@pytest.mark.django_db
def test_options_are_rejected_for_rating_scale_question(question_service):
    provider = create_user("provider-rating-options@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey, QuestionType.RATING_SCALE)

    with pytest.raises(ValidationError):
        question_service.add_question_options(provider, question.question_id, ["Good"])


@pytest.mark.django_db
def test_add_question_with_options_creates_multiple_choice_question_with_options(
    question_service,
):
    provider = create_user(
        "provider-choice-workflow@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)

    question = question_service.add_question_with_options(
        provider,
        survey.survey_id,
        "Choose one option.",
        QuestionType.MULTIPLE_CHOICE,
        True,
        1,
        "Good\nAverage\nPoor",
    )
    options = QuestionRepository().find_options_by_question_id(question.question_id)

    assert question.question_type == QuestionType.MULTIPLE_CHOICE
    assert [option.option_text for option in options] == ["Good", "Average", "Poor"]


@pytest.mark.django_db
def test_add_question_with_options_creates_open_text_question_without_options(
    question_service,
):
    provider = create_user(
        "provider-open-workflow@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)

    question = question_service.add_question_with_options(
        provider,
        survey.survey_id,
        "Tell us more.",
        QuestionType.OPEN_TEXT,
        True,
        0,
        "",
    )
    options = QuestionRepository().find_options_by_question_id(question.question_id)

    assert question.question_type == QuestionType.OPEN_TEXT
    assert list(options) == []


@pytest.mark.django_db
def test_add_question_with_options_rejects_options_for_open_text_question(
    question_service,
):
    provider = create_user(
        "provider-open-workflow-options@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)

    with pytest.raises(ValidationError):
        question_service.add_question_with_options(
            provider,
            survey.survey_id,
            "Tell us more.",
            QuestionType.OPEN_TEXT,
            True,
            0,
            "Not allowed",
        )


@pytest.mark.django_db
def test_get_response_form_questions_returns_open_text_question_data(question_service):
    provider = create_user("provider-open-form@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(
        question_service,
        provider,
        survey,
        QuestionType.OPEN_TEXT,
        text="Tell us about your experience.",
        order_index=2,
    )

    respondent = make_survey_answerable(survey)

    questions = question_service.get_response_form_questions(respondent, survey.survey_id)

    assert questions[0]["question_id"] == question.question_id
    assert questions[0]["question_text"] == "Tell us about your experience."
    assert questions[0]["question_type"] == QuestionType.OPEN_TEXT
    assert questions[0]["is_required"] is True
    assert questions[0]["order_index"] == 2
    assert questions[0]["options"] == []


@pytest.mark.django_db
def test_get_response_form_questions_returns_rating_scale_question_data(question_service):
    provider = create_user("provider-rating-form@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(
        question_service,
        provider,
        survey,
        QuestionType.RATING_SCALE,
        text="Rate the service.",
        order_index=1,
    )

    respondent = make_survey_answerable(survey)

    questions = question_service.get_response_form_questions(respondent, survey.survey_id)

    assert questions[0]["question_id"] == question.question_id
    assert questions[0]["question_text"] == "Rate the service."
    assert questions[0]["question_type"] == QuestionType.RATING_SCALE
    assert questions[0]["is_required"] is True
    assert questions[0]["order_index"] == 1
    assert questions[0]["options"] == []


@pytest.mark.django_db
def test_get_response_form_questions_returns_multiple_choice_question_with_options(
    question_service,
):
    provider = create_user("provider-choice-form@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(
        question_service,
        provider,
        survey,
        QuestionType.MULTIPLE_CHOICE,
        text="Would you recommend us?",
    )
    options = question_service.add_question_options(
        provider,
        question.question_id,
        ["Yes", "No"],
    )

    respondent = make_survey_answerable(survey)

    questions = question_service.get_response_form_questions(respondent, survey.survey_id)

    assert questions[0]["question_id"] == question.question_id
    assert questions[0]["question_type"] == QuestionType.MULTIPLE_CHOICE
    assert questions[0]["options"] == [
        {
            "option_id": options[0].option_id,
            "option_text": "Yes",
            "order_index": 0,
            "id": options[0].option_id,
            "text": "Yes",
        },
        {
            "option_id": options[1].option_id,
            "option_text": "No",
            "order_index": 1,
            "id": options[1].option_id,
            "text": "No",
        },
    ]


@pytest.mark.django_db
def test_response_form_questions_are_ordered_by_order_index(question_service):
    provider = create_user("provider-question-order@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    second = add_question(
        question_service,
        provider,
        survey,
        text="Second question?",
        order_index=2,
    )
    first = add_question(
        question_service,
        provider,
        survey,
        text="First question?",
        order_index=1,
    )

    respondent = make_survey_answerable(survey)

    questions = question_service.get_response_form_questions(respondent, survey.survey_id)

    assert [question["question_id"] for question in questions] == [
        first.question_id,
        second.question_id,
    ]


@pytest.mark.django_db
def test_response_form_options_are_ordered_by_order_index(question_service):
    provider = create_user("provider-option-order@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(
        question_service,
        provider,
        survey,
        QuestionType.MULTIPLE_CHOICE,
    )
    second = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="Second", order_index=2)
    )
    first = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="First", order_index=1)
    )

    respondent = make_survey_answerable(survey)

    questions = question_service.get_response_form_questions(respondent, survey.survey_id)

    assert [option["option_id"] for option in questions[0]["options"]] == [
        first.option_id,
        second.option_id,
    ]


@pytest.mark.django_db
def test_get_survey_question_rows_returns_questions_ordered_by_order_index(
    question_service,
):
    provider = create_user(
        "provider-management-question-order@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    second = add_question(
        question_service,
        provider,
        survey,
        text="Second question?",
        order_index=2,
    )
    first = add_question(
        question_service,
        provider,
        survey,
        text="First question?",
        order_index=1,
    )

    rows = question_service.get_survey_question_rows(provider, survey.survey_id)

    assert [row["question_id"] for row in rows] == [
        first.question_id,
        second.question_id,
    ]


@pytest.mark.django_db
def test_get_survey_question_rows_returns_options_ordered_by_order_index(
    question_service,
):
    provider = create_user(
        "provider-management-option-order@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    question = add_question(
        question_service,
        provider,
        survey,
        QuestionType.MULTIPLE_CHOICE,
    )
    second = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="Second", order_index=2)
    )
    first = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="First", order_index=1)
    )

    rows = question_service.get_survey_question_rows(provider, survey.survey_id)

    assert rows[0]["options"] == [
        {
            "option_id": first.option_id,
            "option_text": "First",
            "order_index": 1,
        },
        {
            "option_id": second.option_id,
            "option_text": "Second",
            "order_index": 2,
        },
    ]


@pytest.mark.django_db
def test_non_owner_cannot_get_survey_question_rows(question_service):
    owner = create_user(
        "owner-management-rows@example.com",
        UserType.SERVICE_PROVIDER,
    )
    other_provider = create_user(
        "other-management-rows@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(owner)

    with pytest.raises(UnauthorizedAction):
        question_service.get_survey_question_rows(other_provider, survey.survey_id)


@pytest.mark.django_db
def test_provider_can_update_question_in_own_draft_survey(question_service):
    provider = create_user("provider-update-question@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey)

    updated = question_service.update_question(
        provider,
        question.question_id,
        "Updated question?",
        False,
        3,
    )

    assert updated.question_text == "Updated question?"
    assert updated.is_required is False
    assert updated.order_index == 3


@pytest.mark.django_db
def test_provider_can_delete_question_in_own_draft_survey(question_service):
    provider = create_user("provider-delete-question@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey)

    question_service.delete_question(provider, question.question_id)

    assert QuestionRepository().find_by_id(question.question_id) is None


@pytest.mark.django_db
def test_provider_cannot_delete_question_in_published_survey(question_service):
    provider = create_user(
        "provider-delete-question-published@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey)
    publish_survey(survey)

    with pytest.raises(NotEditable):
        question_service.delete_question(provider, question.question_id)


@pytest.mark.django_db
def test_provider_cannot_delete_question_in_closed_survey(question_service):
    provider = create_user(
        "provider-delete-question-closed@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    question = add_question(question_service, provider, survey)
    close_survey(publish_survey(survey))

    with pytest.raises(NotEditable):
        question_service.delete_question(provider, question.question_id)


@pytest.mark.django_db
def test_provider_cannot_delete_another_providers_question(question_service):
    owner = create_user("owner-delete-question@example.com", UserType.SERVICE_PROVIDER)
    other_provider = create_user(
        "other-delete-question@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(owner)
    question = add_question(question_service, owner, survey)

    with pytest.raises(UnauthorizedAction):
        question_service.delete_question(other_provider, question.question_id)


class FailingSecondOptionQuestionRepository(QuestionRepository):
    def __init__(self):
        self.option_saves = 0

    def save_option(self, option):
        self.option_saves += 1
        if self.option_saves == 2:
            raise RuntimeError("Option storage failed.")
        return super().save_option(option)


@pytest.mark.django_db
def test_add_question_options_rolls_back_all_options_when_a_write_fails():
    service = QuestionService(question_repository=FailingSecondOptionQuestionRepository())
    provider = create_user("provider-options-rollback@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = add_question(service, provider, survey, QuestionType.MULTIPLE_CHOICE)

    with pytest.raises(RuntimeError):
        service.add_question_options(provider, question.question_id, ["Good", "Poor"])

    assert not QuestionOption.objects.filter(question_id=question.question_id).exists()


@pytest.mark.django_db
def test_get_response_form_questions_rejects_respondent_not_matching_targeting(
    question_service,
):
    provider = create_user("provider-form-target@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    add_question(question_service, provider, survey)
    respondent = make_survey_answerable(survey, target_gender=Gender.MALE)

    with pytest.raises(UnauthorizedAction):
        question_service.get_response_form_questions(respondent, survey.survey_id)


@pytest.mark.django_db
def test_get_response_form_questions_rejects_draft_survey(question_service):
    provider = create_user("provider-form-draft@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    add_question(question_service, provider, survey)
    respondent = make_survey_answerable(survey)
    survey.status = SurveyStatus.DRAFT
    SurveyRepository().update(survey)

    with pytest.raises(NotEditable):
        question_service.get_response_form_questions(respondent, survey.survey_id)


@pytest.mark.django_db
def test_get_response_form_questions_rejects_missing_survey(question_service):
    respondent = create_user("respondent-form-missing@example.com", UserType.RESPONDENT)

    with pytest.raises(SurveyNotFound):
        question_service.get_response_form_questions(respondent, 999999)


@pytest.mark.django_db
def test_get_response_form_questions_rejects_non_respondent(question_service):
    provider = create_user("provider-form-role@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    add_question(question_service, provider, survey)
    make_survey_answerable(survey)

    with pytest.raises(UnauthorizedAction):
        question_service.get_response_form_questions(provider, survey.survey_id)
