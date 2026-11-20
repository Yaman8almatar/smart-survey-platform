"""FR-12 (TASK-54): the provider submits a draft; an admin approves or rejects it with a reason."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.models import Question, QuestionOption, RespondentProfile, Survey, User
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import (
    NotEditable,
    SurveyNotFound,
    TargetingCriteriaNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.survey_repository import SurveyRepository
from repositories.targeting_repository import TargetingRepository
from services.question_service import QuestionService
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService
from services.targeting_service import TargetingService
from tests.review_helpers import create_admin, publish_through_review

pytestmark = pytest.mark.django_db

ROLE_ERROR = "^Only admins can perform this action.$"
NOT_WAITING = "^This survey is no longer waiting for review.$"


def make_user(email, user_type, name="Test User"):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name=name,
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def add_profile(email, gender=Gender.FEMALE):
    respondent = make_user(email, UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=respondent, age=30, gender=gender, region="DAMASCUS", interests=["TECHNOLOGY"]
    )
    return respondent


def ready_draft(provider, title="Review me", gender=Gender.ANY):
    """A draft that passes every submit check: one question and targeting criteria."""
    survey = SurveyService().create_survey(provider, title, "What we ask and why.")
    Question.objects.create(
        survey=survey,
        question_text="How was the service?",
        question_type=QuestionType.OPEN_TEXT,
        is_required=True,
        order_index=0,
    )
    TargetingRepository().create_or_update(survey=survey, gender=gender)
    return survey


def stored(survey):
    return Survey.objects.get(pk=survey.pk)


@pytest.fixture
def provider():
    return make_user("provider-review@example.com", UserType.SERVICE_PROVIDER, "Rana Provider")


@pytest.fixture
def admin():
    return create_admin("admin-review@example.com")


@pytest.fixture
def pending(provider):
    survey = ready_draft(provider)
    SurveyService().submit_for_review(provider, survey.survey_id)
    return stored(survey)


# Submit


def test_submit_moves_the_draft_to_pending_review(provider):
    survey = ready_draft(provider)

    SurveyService().submit_for_review(provider, survey.survey_id)

    survey = stored(survey)
    assert survey.status == SurveyStatus.PENDING_REVIEW
    assert survey.submitted_at is not None
    assert survey.published_at is None
    assert survey.reach_at_publish is None


def test_a_second_submit_clears_the_last_rejection(provider, pending, admin):
    SurveyReviewService().reject(admin, pending.survey_id, "Fix question 1.")

    SurveyService().submit_for_review(provider, pending.survey_id)

    survey = stored(pending)
    assert survey.status == SurveyStatus.PENDING_REVIEW
    assert survey.rejection_reason == ""
    assert survey.reviewed_at is None
    assert survey.reviewed_by is None


def _no_question(provider):
    survey = SurveyService().create_survey(provider, "No question", "")
    TargetingRepository().create_or_update(survey=survey, gender=Gender.ANY)
    return survey


def _one_option(provider):
    survey = SurveyService().create_survey(provider, "One option", "")
    question = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=0,
    )
    QuestionOption.objects.create(question=question, option_text="Only", order_index=0)
    TargetingRepository().create_or_update(survey=survey, gender=Gender.ANY)
    return survey


def _no_criteria(provider):
    survey = SurveyService().create_survey(provider, "No criteria", "")
    Question.objects.create(
        survey=survey,
        question_text="How was it?",
        question_type=QuestionType.OPEN_TEXT,
        is_required=True,
        order_index=0,
    )
    return survey


@pytest.mark.parametrize(
    "build, error, message",
    [
        (_no_question, ValidationError, "^A survey must have at least one question.$"),
        (
            _one_option,
            ValidationError,
            "^Multiple-choice questions need at least two options before publishing.$",
        ),
        (_no_criteria, TargetingCriteriaNotFound, "^Survey targeting criteria is required.$"),
    ],
)
def test_submit_runs_every_publish_check(provider, build, error, message):
    survey = build(provider)

    with pytest.raises(error, match=message):
        SurveyService().submit_for_review(provider, survey.survey_id)

    assert stored(survey).status == SurveyStatus.DRAFT


def test_only_the_owner_can_submit(provider):
    other = make_user("other-review@example.com", UserType.SERVICE_PROVIDER)
    survey = ready_draft(provider)

    with pytest.raises(UnauthorizedAction, match="^Only the survey owner can perform this action.$"):
        SurveyService().submit_for_review(other, survey.survey_id)


def test_only_a_draft_can_be_submitted(provider, pending):
    with pytest.raises(NotEditable, match="^Only draft surveys can be submitted for review.$"):
        SurveyService().submit_for_review(provider, pending.survey_id)


# Approve


def test_approve_publishes_and_records_the_review(pending, admin):
    SurveyReviewService().approve(admin, pending.survey_id)

    survey = stored(pending)
    assert survey.status == SurveyStatus.PUBLISHED
    assert survey.published_at is not None
    assert survey.reviewed_by == admin
    assert survey.reviewed_at is not None
    assert survey.rejection_reason == ""


def test_approve_counts_the_reach_at_approval(pending, admin):
    add_profile("respondent-after-submit@example.com")

    SurveyReviewService().approve(admin, pending.survey_id)

    assert stored(pending).reach_at_publish == 1


def test_approve_reads_the_survey_with_the_locked_read(pending, admin):
    calls = []

    class SpyRepository(SurveyRepository):
        def find_by_id_for_update(self, survey_id):
            calls.append(survey_id)
            return super().find_by_id_for_update(survey_id)

    SurveyReviewService(survey_repository=SpyRepository()).approve(admin, pending.survey_id)

    assert calls == [pending.survey_id]


# Reject


def test_reject_returns_the_survey_to_draft_with_the_stripped_reason(pending, admin):
    SurveyReviewService().reject(admin, pending.survey_id, "  Question 2 is leading.  ")

    survey = stored(pending)
    assert survey.status == SurveyStatus.DRAFT
    assert survey.rejection_reason == "Question 2 is leading."
    assert survey.reviewed_by == admin
    assert survey.reviewed_at is not None
    assert survey.published_at is None


@pytest.mark.parametrize("reason", ["", "    ", None])
def test_reject_needs_a_reason(pending, admin, reason):
    with pytest.raises(ValidationError, match="^Write a reason for the provider.$"):
        SurveyReviewService().reject(admin, pending.survey_id, reason)

    assert stored(pending).status == SurveyStatus.PENDING_REVIEW


def test_reject_refuses_a_reason_over_1000_characters(pending, admin):
    with pytest.raises(ValidationError, match="^The reason must be 1000 characters or fewer.$"):
        SurveyReviewService().reject(admin, pending.survey_id, "x" * 1001)

    assert stored(pending).status == SurveyStatus.PENDING_REVIEW


def test_reject_accepts_exactly_1000_characters(pending, admin):
    SurveyReviewService().reject(admin, pending.survey_id, "x" * 1000)

    assert stored(pending).rejection_reason == "x" * 1000


# Only a pending survey is decided on


def _draft(provider):
    return ready_draft(provider)


def _published(provider):
    survey = ready_draft(provider)
    return publish_through_review(provider, survey.survey_id)


@pytest.mark.parametrize("build", [_draft, _published])
@pytest.mark.parametrize("decide", ["approve", "reject"])
def test_a_survey_not_pending_cannot_be_decided(provider, admin, build, decide):
    survey = build(provider)
    status = stored(survey).status
    service = SurveyReviewService()

    with pytest.raises(NotEditable, match=NOT_WAITING):
        if decide == "approve":
            service.approve(admin, survey.survey_id)
        else:
            service.reject(admin, survey.survey_id, "Too late.")

    assert stored(survey).status == status


@pytest.mark.parametrize("decide", ["approve", "reject"])
def test_an_approved_survey_cannot_be_decided_again(pending, admin, decide):
    service = SurveyReviewService()
    service.approve(admin, pending.survey_id)

    with pytest.raises(NotEditable, match=NOT_WAITING):
        if decide == "approve":
            service.approve(admin, pending.survey_id)
        else:
            service.reject(admin, pending.survey_id, "Second thoughts.")

    assert stored(pending).status == SurveyStatus.PUBLISHED


def test_get_review_of_a_survey_not_pending_raises(provider, admin):
    survey = ready_draft(provider)

    with pytest.raises(NotEditable, match=NOT_WAITING):
        SurveyReviewService().get_review(admin, survey.survey_id)


@pytest.mark.parametrize(
    "call",
    [
        lambda service, admin: service.get_review(admin, 999999),
        lambda service, admin: service.approve(admin, 999999),
        lambda service, admin: service.reject(admin, 999999, "Reason"),
    ],
)
def test_a_missing_survey_raises_not_found(admin, call):
    with pytest.raises(SurveyNotFound, match="^Survey not found.$"):
        call(SurveyReviewService(), admin)


# Roles


@pytest.mark.parametrize("user_type", [UserType.SERVICE_PROVIDER, UserType.RESPONDENT])
@pytest.mark.parametrize(
    "call",
    [
        lambda service, user, survey_id: service.count_pending(user),
        lambda service, user, survey_id: service.list_pending(user),
        lambda service, user, survey_id: service.get_review(user, survey_id),
        lambda service, user, survey_id: service.approve(user, survey_id),
        lambda service, user, survey_id: service.reject(user, survey_id, "Reason"),
    ],
)
def test_only_an_admin_can_use_the_review(pending, user_type, call):
    user = make_user(f"not-admin-{user_type.lower()}@example.com", user_type)

    with pytest.raises(UnauthorizedAction, match=ROLE_ERROR):
        call(SurveyReviewService(), user, pending.survey_id)

    assert stored(pending).status == SurveyStatus.PENDING_REVIEW


@pytest.mark.parametrize("user_type", [UserType.SERVICE_PROVIDER, UserType.RESPONDENT])
def test_review_question_rows_are_for_admins_only(pending, user_type):
    user = make_user(f"rows-{user_type.lower()}@example.com", user_type)

    with pytest.raises(UnauthorizedAction, match=ROLE_ERROR):
        QuestionService().get_review_question_rows(user, pending.survey_id)


def test_review_question_rows_match_the_providers_rows(provider, pending, admin):
    assert QuestionService().get_review_question_rows(
        admin, pending.survey_id
    ) == QuestionService().get_survey_question_rows(provider, pending.survey_id)


# A pending survey is locked


def test_a_pending_survey_cannot_be_changed(provider, pending):
    survey_id = pending.survey_id

    with pytest.raises(NotEditable):
        SurveyService().update_survey(provider, survey_id, "New title", "")
    with pytest.raises(NotEditable):
        SurveyService().delete_survey(provider, survey_id)
    with pytest.raises(NotEditable):
        SurveyService().close_survey(provider, survey_id)
    with pytest.raises(NotEditable):
        QuestionService().add_question(
            provider, survey_id, "One more?", QuestionType.OPEN_TEXT, True, 1
        )
    with pytest.raises(NotEditable):
        TargetingService().save_criteria(provider, survey_id, gender=Gender.MALE)

    assert stored(pending).status == SurveyStatus.PENDING_REVIEW


def test_a_pending_survey_is_not_in_a_matching_respondents_list(pending):
    respondent = add_profile("respondent-pending@example.com")

    items = SurveyService().get_eligible_survey_items(respondent)

    assert pending.survey_id not in [item["survey"].survey_id for item in items]


# The list and the review page


def test_the_list_holds_pending_surveys_only_oldest_first(provider, admin):
    newer = ready_draft(provider, "Newer")
    older = ready_draft(provider, "Older")
    draft = ready_draft(provider, "Still a draft")
    published = publish_through_review(provider, ready_draft(provider, "Live").survey_id)
    for survey in (newer, older):
        SurveyService().submit_for_review(provider, survey.survey_id)
    now = timezone.now()
    Survey.objects.filter(pk=older.pk).update(submitted_at=now - timedelta(days=2))
    Survey.objects.filter(pk=newer.pk).update(submitted_at=now - timedelta(days=1))

    rows = SurveyReviewService().list_pending(admin)

    assert [row["survey"].survey_id for row in rows] == [older.survey_id, newer.survey_id]
    assert draft.survey_id not in [row["survey"].survey_id for row in rows]
    assert published.survey_id not in [row["survey"].survey_id for row in rows]
    assert rows[0]["provider_name"] == "Rana Provider"
    assert rows[0]["provider_email"] == "provider-review@example.com"
    assert rows[0]["submitted_at"] == now - timedelta(days=2)
    assert rows[0]["question_count"] == 1


def test_count_pending_counts_the_waiting_surveys(provider, admin):
    assert SurveyReviewService().count_pending(admin) == 0
    for title in ("One", "Two"):
        survey = ready_draft(provider, title)
        SurveyService().submit_for_review(provider, survey.survey_id)
    ready_draft(provider, "Draft")

    assert SurveyReviewService().count_pending(admin) == 2


def test_get_review_returns_the_survey_its_targeting_and_questions(provider, admin):
    add_profile("respondent-review-page@example.com")
    survey = ready_draft(provider, gender=Gender.FEMALE)
    SurveyService().submit_for_review(provider, survey.survey_id)

    review = SurveyReviewService().get_review(admin, survey.survey_id)

    assert review["survey"].survey_id == survey.survey_id
    assert review["provider_name"] == "Rana Provider"
    assert review["provider_email"] == "provider-review@example.com"
    assert review["submitted_at"] == stored(survey).submitted_at
    assert review["criteria"]["gender"] == Gender.FEMALE
    assert review["reach"]["total"] == 1
    assert [row["text"] for row in review["questions"]] == ["How was the service?"]
