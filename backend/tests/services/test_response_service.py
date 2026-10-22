import pytest

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    Survey,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import (
    DuplicateResponse,
    NotEditable,
    UnauthorizedAction,
    ValidationError,
)
from repositories.profile_repository import ProfileRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.response_service import ResponseService


class FakeAnalysisService:
    def __init__(self):
        self.calls = []

    def analyze_open_text_answers(self, response_id):
        self.calls.append(response_id)


@pytest.fixture
def fake_analysis_service():
    return FakeAnalysisService()


@pytest.fixture
def response_service(fake_analysis_service):
    return ResponseService(analysis_service=fake_analysis_service)


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_profile(user, gender=Gender.FEMALE, age=30, region="Damascus"):
    return ProfileRepository().save(
        RespondentProfile(
            user=user,
            age=age,
            gender=gender,
            region=region,
            interests="Technology",
        )
    )


def create_survey(provider, status=SurveyStatus.PUBLISHED, gender=Gender.ANY):
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    TargetingRepository().create_or_update(survey=survey, gender=gender)

    if status == SurveyStatus.PUBLISHED:
        survey.publish()
        SurveyRepository().update(survey)
    elif status == SurveyStatus.CLOSED:
        survey.publish()
        survey.close()
        SurveyRepository().update(survey)

    return survey


def create_question(survey, question_type, is_required=True):
    return QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Question?",
            question_type=question_type,
            is_required=is_required,
            order_index=0,
        )
    )


def create_option(question, text="Option"):
    return QuestionRepository().save_option(
        QuestionOption(question=question, option_text=text, order_index=0)
    )


def open_text_answer(question, value="Good service"):
    return {
        "question_id": question.question_id,
        "answer_value": value,
        "rating_value": None,
        "selected_option_id": None,
    }


def rating_answer(question, value=5):
    return {
        "question_id": question.question_id,
        "answer_value": None,
        "rating_value": value,
        "selected_option_id": None,
    }


def choice_answer(question, option):
    return {
        "question_id": question.question_id,
        "answer_value": None,
        "rating_value": None,
        "selected_option_id": option.option_id,
    }


@pytest.mark.django_db
def test_respondent_can_submit_valid_response(response_service):
    provider = create_user("provider-submit@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-submit@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [open_text_answer(question)],
    )

    assert response.survey == survey
    assert response.respondent == respondent


@pytest.mark.django_db
def test_non_respondent_cannot_submit_response(response_service):
    provider = create_user(
        "provider-non-respondent@example.com",
        UserType.SERVICE_PROVIDER,
    )
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(UnauthorizedAction):
        response_service.submit_response(
            provider,
            survey.survey_id,
            [open_text_answer(question)],
        )


@pytest.mark.django_db
def test_response_to_draft_survey_is_rejected(response_service):
    provider = create_user(
        "provider-draft-response@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user("respondent-draft-response@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider, status=SurveyStatus.DRAFT)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(NotEditable):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )


@pytest.mark.django_db
def test_response_to_closed_survey_is_rejected(response_service):
    provider = create_user(
        "provider-closed-response@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-closed-response@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider, status=SurveyStatus.CLOSED)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(NotEditable):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )


@pytest.mark.django_db
def test_duplicate_response_is_rejected(response_service):
    provider = create_user(
        "provider-duplicate-response@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-duplicate-response@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)
    ResponseRepository().save(Response(survey=survey, respondent=respondent))

    with pytest.raises(DuplicateResponse):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )


@pytest.mark.django_db
def test_respondent_can_list_answered_surveys(response_service):
    provider = create_user(
        "provider-answered-list@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-answered-list@example.com",
        UserType.RESPONDENT,
    )
    survey = create_survey(provider)
    ResponseRepository().save(Response(survey=survey, respondent=respondent))

    answered_surveys = response_service.get_answered_surveys(respondent)
    answered_survey = answered_surveys[0]

    assert len(answered_surveys) == 1
    assert answered_survey["survey_id"] == survey.survey_id
    assert answered_survey["survey_title"] == survey.title
    assert answered_survey["survey_description"] == survey.description
    assert answered_survey["submitted_at"] is not None


@pytest.mark.django_db
def test_non_respondent_cannot_list_answered_surveys(response_service):
    provider = create_user(
        "provider-answered-denied@example.com",
        UserType.SERVICE_PROVIDER,
    )

    with pytest.raises(UnauthorizedAction):
        response_service.get_answered_surveys(provider)


@pytest.mark.django_db
def test_unanswered_surveys_are_not_in_answered_surveys(response_service):
    provider = create_user(
        "provider-unanswered-excluded@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-unanswered-excluded@example.com",
        UserType.RESPONDENT,
    )
    answered_survey = create_survey(provider)
    unanswered_survey = create_survey(provider)
    ResponseRepository().save(Response(survey=answered_survey, respondent=respondent))

    answered_surveys = response_service.get_answered_surveys(respondent)
    answered_survey_ids = {item["survey_id"] for item in answered_surveys}

    assert answered_survey.survey_id in answered_survey_ids
    assert unanswered_survey.survey_id not in answered_survey_ids


@pytest.mark.django_db
def test_respondent_not_matching_targeting_criteria_is_rejected(response_service):
    provider = create_user(
        "provider-target-mismatch@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-target-mismatch@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent, gender=Gender.FEMALE)
    survey = create_survey(provider, gender=Gender.MALE)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(UnauthorizedAction):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )


@pytest.mark.django_db
def test_missing_required_answer_is_rejected(response_service):
    provider = create_user(
        "provider-missing-answer@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-missing-answer@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(ValidationError):
        response_service.submit_response(respondent, survey.survey_id, [])


@pytest.mark.django_db
def test_open_text_answer_is_saved_correctly(response_service):
    provider = create_user(
        "provider-open-text-save@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-open-text-save@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [open_text_answer(question, "Excellent")],
    )
    answer = ResponseRepository().find_answers_by_response_id(response.response_id).first()

    assert answer.answer_value == "Excellent"
    assert answer.rating_value is None
    assert answer.selected_option is None


@pytest.mark.django_db
def test_rating_scale_answer_is_saved_correctly(response_service):
    provider = create_user("provider-rating-save@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user(
        "respondent-rating-save@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.RATING_SCALE)

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [rating_answer(question, 4)],
    )
    answer = ResponseRepository().find_answers_by_response_id(response.response_id).first()

    assert answer.rating_value == 4
    assert answer.answer_value is None
    assert answer.selected_option is None


@pytest.mark.django_db
def test_multiple_choice_answer_is_saved_correctly(response_service):
    provider = create_user("provider-choice-save@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user(
        "respondent-choice-save@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    option = create_option(question, "Good")

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [choice_answer(question, option)],
    )
    answer = ResponseRepository().find_answers_by_response_id(response.response_id).first()

    assert answer.selected_option == option
    assert answer.answer_value is None
    assert answer.rating_value is None


@pytest.mark.django_db
def test_selected_option_from_another_question_is_rejected(response_service):
    provider = create_user("provider-wrong-option@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user(
        "respondent-wrong-option@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    other_question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    other_option = create_option(other_question, "Other")

    with pytest.raises(ValidationError):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [choice_answer(question, other_option)],
        )


@pytest.mark.django_db
def test_open_text_response_triggers_analysis_service(
    response_service,
    fake_analysis_service,
):
    provider = create_user(
        "provider-analysis-trigger@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-analysis-trigger@example.com",
        UserType.RESPONDENT,
    )
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [open_text_answer(question)],
    )

    assert fake_analysis_service.calls == [response.response_id]


@pytest.mark.django_db
def test_response_without_open_text_answers_does_not_trigger_analysis_service(
    response_service,
    fake_analysis_service,
):
    provider = create_user("provider-no-analysis@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-no-analysis@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.RATING_SCALE)

    response_service.submit_response(
        respondent,
        survey.survey_id,
        [rating_answer(question, 5)],
    )

    assert fake_analysis_service.calls == []


@pytest.mark.django_db
def test_validate_duplicate_response_returns_true_when_response_exists(response_service):
    provider = create_user(
        "provider-duplicate-true@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-duplicate-true@example.com",
        UserType.RESPONDENT,
    )
    survey = create_survey(provider)
    ResponseRepository().save(Response(survey=survey, respondent=respondent))

    assert response_service.validate_duplicate_response(respondent, survey.survey_id) is True


@pytest.mark.django_db
def test_validate_duplicate_response_returns_false_when_response_does_not_exist(
    response_service,
):
    provider = create_user(
        "provider-duplicate-false@example.com",
        UserType.SERVICE_PROVIDER,
    )
    respondent = create_user(
        "respondent-duplicate-false@example.com",
        UserType.RESPONDENT,
    )
    survey = create_survey(provider)

    assert response_service.validate_duplicate_response(respondent, survey.survey_id) is False
