import pytest

from apps.core.models import QuestionOption, Survey, User
from core.enums import AccountStatus, QuestionType, UserType
from core.exceptions import NotEditable, UnauthorizedAction, ValidationError
from repositories.question_repository import QuestionRepository
from repositories.survey_repository import SurveyRepository
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

    questions = question_service.get_response_form_questions(survey.survey_id)

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

    questions = question_service.get_response_form_questions(survey.survey_id)

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

    questions = question_service.get_response_form_questions(survey.survey_id)

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

    questions = question_service.get_response_form_questions(survey.survey_id)

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

    questions = question_service.get_response_form_questions(survey.survey_id)

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
