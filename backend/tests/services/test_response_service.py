import logging
import threading
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError, connection, transaction

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    ResponseDraft,
    Survey,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import (
    DraftNotFound,
    DuplicateResponse,
    NotEditable,
    QuestionNotFound,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.draft_repository import DraftRepository
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


def create_profile(user, gender=Gender.FEMALE, age=30, region="DAMASCUS"):
    return ProfileRepository().save(
        RespondentProfile(
            user=user,
            age=age,
            gender=gender,
            region=region,
            interests=["TECHNOLOGY"],
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
def test_open_text_answer_over_2000_characters_is_rejected(response_service):
    provider = create_user("provider-long-text@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-long-text@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with pytest.raises(ValidationError):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question, "x" * 2001)],
        )

    assert not ResponseRepository().has_response_for_survey(
        survey.survey_id, respondent.user_id
    )


@pytest.mark.django_db
def test_open_text_answer_of_exactly_2000_characters_is_accepted(response_service):
    provider = create_user("provider-limit-text@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-limit-text@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    response = response_service.submit_response(
        respondent,
        survey.survey_id,
        [open_text_answer(question, "x" * 2000)],
    )

    assert response.response_id is not None


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
    django_capture_on_commit_callbacks,
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

    with django_capture_on_commit_callbacks(execute=True):
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
    django_capture_on_commit_callbacks,
):
    provider = create_user("provider-no-analysis@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-no-analysis@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.RATING_SCALE)

    with django_capture_on_commit_callbacks(execute=True):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [rating_answer(question, 5)],
        )

    assert fake_analysis_service.calls == []


@pytest.mark.django_db
def test_analysis_runs_only_after_response_commit(
    response_service,
    fake_analysis_service,
    django_capture_on_commit_callbacks,
):
    provider = create_user("provider-after-commit@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-after-commit@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        response = response_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )
        assert fake_analysis_service.calls == []

    assert len(callbacks) == 1
    callbacks[0]()
    assert fake_analysis_service.calls == [response.response_id]


class FailingAnswerResponseRepository(ResponseRepository):
    def save_answer(self, answer):
        raise RuntimeError("Answer storage failed.")


@pytest.mark.django_db
def test_submit_response_rolls_back_when_answer_save_fails(fake_analysis_service):
    provider = create_user("provider-rollback@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-rollback@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)
    failing_service = ResponseService(
        response_repository=FailingAnswerResponseRepository(),
        analysis_service=fake_analysis_service,
    )

    with pytest.raises(RuntimeError):
        failing_service.submit_response(
            respondent,
            survey.survey_id,
            [open_text_answer(question)],
        )

    assert not Response.objects.filter(survey=survey, respondent=respondent).exists()

    response = ResponseService(analysis_service=fake_analysis_service).submit_response(
        respondent,
        survey.survey_id,
        [open_text_answer(question)],
    )
    assert response.response_id is not None


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


def create_rating_survey(suffix):
    provider = create_user(f"provider-{suffix}@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user(f"respondent-{suffix}@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.RATING_SCALE)
    return respondent, survey, question


@pytest.mark.django_db(transaction=True)
def test_parallel_submits_store_one_response():
    respondent, survey, question = create_rating_survey("race")
    barrier = threading.Barrier(2)
    results = []

    def submit_once():
        try:
            service = ResponseService(analysis_service=FakeAnalysisService())
            barrier.wait()
            service.submit_response(respondent, survey.survey_id, [rating_answer(question)])
            results.append("created")
        except DuplicateResponse:
            results.append("duplicate")
        except Exception as exc:  # reported by the assertion below
            results.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=submit_once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["created", "duplicate"]
    assert Response.objects.filter(survey=survey, respondent=respondent).count() == 1


@pytest.mark.django_db
def test_other_integrity_error_is_not_turned_into_duplicate_response(
    response_service, monkeypatch
):
    respondent, survey, question = create_rating_survey("other-constraint")

    def fail_save_answer(answer):
        raise IntegrityError(
            'duplicate key value violates unique constraint "unique_answer_per_response_question"'
        )

    monkeypatch.setattr(response_service.response_repository, "save_answer", fail_save_answer)

    with pytest.raises(IntegrityError):
        response_service.submit_response(
            respondent,
            survey.survey_id,
            [rating_answer(question)],
        )


@pytest.mark.django_db
def test_database_refuses_two_answers_for_one_response_and_question():
    respondent, survey, question = create_rating_survey("answer-constraint")
    repository = ResponseRepository()
    response = repository.save(Response(survey=survey, respondent=respondent))
    repository.save_answer(Answer(response=response, question=question, rating_value=4))

    with pytest.raises(IntegrityError, match="unique_answer_per_response_question"):
        with transaction.atomic():
            repository.save_answer(Answer(response=response, question=question, rating_value=5))


def test_dispatch_logs_celery_failure_and_runs_analysis_directly(
    fake_analysis_service, settings, caplog
):
    settings.CELERY_ENABLED = True
    task = MagicMock()
    task.delay.side_effect = ConnectionError("broker unavailable")
    service = ResponseService(analysis_service=fake_analysis_service)

    with patch("apps.core.tasks.analyze_open_text_answers_task", task):
        with caplog.at_level(logging.ERROR, logger="services.response_service"):
            service._dispatch_sentiment_analysis(42)

    task.delay.assert_called_once_with(42)
    assert fake_analysis_service.calls == [42]
    [record] = caplog.records
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None


def test_dispatch_without_celery_never_calls_delay(
    fake_analysis_service, settings, monkeypatch
):
    settings.CELERY_ENABLED = False
    # Only the setting decides; the raw environment variable is not read again.
    monkeypatch.setenv("USE_CELERY", "true")
    task = MagicMock()
    service = ResponseService(analysis_service=fake_analysis_service)

    with patch("apps.core.tasks.analyze_open_text_answers_task", task):
        service._dispatch_sentiment_analysis(7)

    task.delay.assert_not_called()
    assert fake_analysis_service.calls == [7]


# Response drafts (FR-06)

DRAFT_OPERATIONS = {
    "get": lambda service, user, survey_id: service.get_draft(user, survey_id),
    "save": lambda service, user, survey_id: service.save_draft(user, survey_id, []),
    "delete": lambda service, user, survey_id: service.delete_draft(user, survey_id),
}


def draft_parties(status=SurveyStatus.PUBLISHED, gender=Gender.ANY):
    provider = create_user("provider-draft@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-draft@example.com", UserType.RESPONDENT)
    create_profile(respondent)
    return provider, respondent, create_survey(provider, status=status, gender=gender)


@pytest.mark.django_db
def test_first_save_creates_draft_with_started_at(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.OPEN_TEXT)

    draft = response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(question, "So far")]
    )

    assert draft.started_at is not None
    assert ResponseDraft.objects.filter(survey=survey, respondent=respondent).count() == 1


@pytest.mark.django_db
def test_stored_draft_answer_keeps_only_non_null_keys(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.RATING_SCALE)

    draft = response_service.save_draft(
        respondent, survey.survey_id, [rating_answer(question, 3)]
    )

    assert draft.answers == [{"question_id": question.question_id, "rating_value": 3}]


@pytest.mark.django_db
def test_second_save_replaces_answers_and_keeps_started_at(response_service):
    _, respondent, survey = draft_parties()
    first = create_question(survey, QuestionType.OPEN_TEXT)
    second = create_question(survey, QuestionType.RATING_SCALE)
    created = response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(first, "Old")]
    )

    response_service.save_draft(respondent, survey.survey_id, [rating_answer(second, 2)])

    stored = ResponseDraft.objects.get(survey=survey, respondent=respondent)
    assert stored.answers == [{"question_id": second.question_id, "rating_value": 2}]
    assert stored.started_at == created.started_at


@pytest.mark.django_db
def test_parallel_first_save_updates_the_existing_draft(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    winner = response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(question, "Winner")]
    )
    real_find = DraftRepository.find
    first_lookup = iter([None])

    # The first lookup misses the row, as it does when another request has not committed yet.
    with patch.object(
        DraftRepository,
        "find",
        autospec=True,
        side_effect=lambda *args: next(first_lookup, real_find(*args)),
    ):
        response_service.save_draft(
            respondent, survey.survey_id, [open_text_answer(question, "Loser retried")]
        )

    stored = ResponseDraft.objects.get(survey=survey, respondent=respondent)
    assert stored.answers[0]["answer_value"] == "Loser retried"
    assert stored.started_at == winner.started_at


@pytest.mark.django_db
def test_empty_answer_list_is_stored(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(question, "Old")]
    )

    draft = response_service.save_draft(respondent, survey.survey_id, [])

    assert draft.answers == []
    assert ResponseDraft.objects.get(pk=draft.pk).answers == []


@pytest.mark.django_db
def test_get_draft_returns_the_saved_draft(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    saved = response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(question, "Kept")]
    )

    draft = response_service.get_draft(respondent, survey.survey_id)

    assert draft.pk == saved.pk
    assert draft.answers == [
        {"question_id": question.question_id, "answer_value": "Kept"}
    ]


@pytest.mark.django_db
def test_get_draft_without_draft_raises(response_service):
    _, respondent, survey = draft_parties()

    with pytest.raises(DraftNotFound, match="No draft for this survey."):
        response_service.get_draft(respondent, survey.survey_id)


@pytest.mark.django_db
def test_delete_draft_removes_it(response_service):
    _, respondent, survey = draft_parties()
    response_service.save_draft(respondent, survey.survey_id, [])

    response_service.delete_draft(respondent, survey.survey_id)

    assert not ResponseDraft.objects.filter(survey=survey, respondent=respondent).exists()


@pytest.mark.django_db
def test_delete_draft_without_draft_raises_nothing(response_service):
    _, respondent, survey = draft_parties()

    response_service.delete_draft(respondent, survey.survey_id)

    assert not ResponseDraft.objects.filter(survey=survey, respondent=respondent).exists()


@pytest.mark.django_db
def test_draft_rejects_question_of_another_survey(response_service):
    provider, respondent, survey = draft_parties()
    other_question = create_question(create_survey(provider), QuestionType.OPEN_TEXT)

    with pytest.raises(QuestionNotFound):
        response_service.save_draft(
            respondent, survey.survey_id, [open_text_answer(other_question)]
        )


@pytest.mark.django_db
def test_draft_rejects_option_of_another_question(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    create_option(question)
    other_question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    other_option = create_option(other_question)

    with pytest.raises(ValidationError):
        response_service.save_draft(
            respondent, survey.survey_id, [choice_answer(question, other_option)]
        )


@pytest.mark.django_db
@pytest.mark.parametrize("rating", [0, 6])
def test_draft_rejects_rating_out_of_range(response_service, rating):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.RATING_SCALE)

    with pytest.raises(ValidationError):
        response_service.save_draft(
            respondent, survey.survey_id, [rating_answer(question, rating)]
        )


@pytest.mark.django_db
def test_draft_rejects_rating_with_answer_value(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.RATING_SCALE)
    answer = {**rating_answer(question, 3), "answer_value": "Text"}

    with pytest.raises(ValidationError):
        response_service.save_draft(respondent, survey.survey_id, [answer])


@pytest.mark.django_db
def test_draft_allows_required_question_missing_or_empty(response_service):
    _, respondent, survey = draft_parties()
    empty = create_question(survey, QuestionType.OPEN_TEXT, is_required=True)
    create_question(survey, QuestionType.RATING_SCALE, is_required=True)

    draft = response_service.save_draft(
        respondent, survey.survey_id, [open_text_answer(empty, "")]
    )

    assert draft.answers == [{"question_id": empty.question_id, "answer_value": ""}]


@pytest.mark.django_db
def test_draft_rejects_duplicate_question(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = open_text_answer(question)

    with pytest.raises(ValidationError):
        response_service.save_draft(respondent, survey.survey_id, [answer, answer])


@pytest.mark.django_db
@pytest.mark.parametrize("operation", DRAFT_OPERATIONS)
def test_draft_operation_rejects_provider(response_service, operation):
    provider, _, survey = draft_parties()

    with pytest.raises(UnauthorizedAction):
        DRAFT_OPERATIONS[operation](response_service, provider, survey.survey_id)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", DRAFT_OPERATIONS)
def test_draft_operation_rejects_unknown_survey(response_service, operation):
    _, respondent, survey = draft_parties()

    with pytest.raises(SurveyNotFound):
        DRAFT_OPERATIONS[operation](response_service, respondent, survey.survey_id + 999)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", DRAFT_OPERATIONS)
def test_draft_operation_rejects_closed_survey(response_service, operation):
    _, respondent, survey = draft_parties(status=SurveyStatus.CLOSED)

    with pytest.raises(NotEditable):
        DRAFT_OPERATIONS[operation](response_service, respondent, survey.survey_id)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", DRAFT_OPERATIONS)
def test_draft_operation_rejects_ineligible_respondent(response_service, operation):
    # The respondent profile is FEMALE.
    _, respondent, survey = draft_parties(gender=Gender.MALE)

    with pytest.raises(UnauthorizedAction):
        DRAFT_OPERATIONS[operation](response_service, respondent, survey.survey_id)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", DRAFT_OPERATIONS)
def test_draft_operation_rejects_answered_survey(response_service, operation):
    _, respondent, survey = draft_parties()
    response_service.submit_response(respondent, survey.survey_id, [])

    with pytest.raises(DuplicateResponse):
        DRAFT_OPERATIONS[operation](response_service, respondent, survey.survey_id)


@pytest.mark.django_db
def test_submit_with_draft_deletes_it_and_copies_started_at(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.RATING_SCALE)
    draft = response_service.save_draft(respondent, survey.survey_id, [])

    response = response_service.submit_response(
        respondent, survey.survey_id, [rating_answer(question, 4)]
    )

    assert response.started_at == draft.started_at
    assert not ResponseDraft.objects.filter(survey=survey, respondent=respondent).exists()


@pytest.mark.django_db
def test_submit_without_draft_leaves_started_at_null(response_service):
    _, respondent, survey = draft_parties()
    question = create_question(survey, QuestionType.RATING_SCALE)

    response = response_service.submit_response(
        respondent, survey.survey_id, [rating_answer(question, 4)]
    )

    assert Response.objects.get(pk=response.pk).started_at is None


@pytest.mark.django_db
def test_failed_submit_keeps_the_draft(response_service):
    _, respondent, survey = draft_parties()
    create_question(survey, QuestionType.RATING_SCALE)
    response_service.save_draft(respondent, survey.survey_id, [])

    with pytest.raises(ValidationError):
        response_service.submit_response(respondent, survey.survey_id, [])

    assert ResponseDraft.objects.filter(survey=survey, respondent=respondent).exists()
