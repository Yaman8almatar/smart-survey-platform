"""FR-11: opening and closing dates, a response limit, pause and resume."""

import datetime
from itertools import count

import pytest
from django.utils import timezone

from apps.core.models import (
    Question,
    RespondentProfile,
    ResponseDraft,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import NotEditable, UnauthorizedAction, ValidationError
from repositories.survey_repository import SurveyRepository
from services.admin_service import AdminService
from services.response_service import ResponseService
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService
from tests.review_helpers import create_admin

pytestmark = pytest.mark.django_db

_numbers = count(1)


def today():
    return timezone.localdate()


def days(n):
    return today() + datetime.timedelta(days=n)


def make_user(user_type):
    return User.objects.create_user(
        email=f"lifecycle-{next(_numbers)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def make_respondent():
    user = make_user(UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=user, age=30, gender=Gender.MALE, region="DAMASCUS", interests=["SPORTS"]
    )
    return user


def make_survey(provider, status=SurveyStatus.PUBLISHED, **fields):
    survey = Survey.objects.create(
        provider=provider, title="Lifecycle survey", status=status, **fields
    )
    TargetingCriteria.objects.create(survey=survey)
    Question.objects.create(
        survey=survey,
        question_text="Rate us",
        question_type=QuestionType.RATING_SCALE,
        is_required=True,
        order_index=0,
    )
    return survey


@pytest.fixture
def provider():
    return make_user(UserType.SERVICE_PROVIDER)


@pytest.fixture
def service():
    return SurveyService()


# --- Model ------------------------------------------------------------------------------


def test_is_open_on_follows_status_and_both_dates():
    survey = Survey(status=SurveyStatus.PUBLISHED)
    assert survey.is_open_on(today())

    survey.opens_on = days(1)
    assert not survey.is_open_on(today())
    survey.opens_on = today()
    survey.closes_on = today()
    assert survey.is_open_on(today())
    survey.closes_on = days(-1)
    assert not survey.is_open_on(today())

    paused = Survey(status=SurveyStatus.PAUSED)
    assert not paused.is_open_on(today())


def test_has_passed_closing_only_after_the_closing_day():
    assert not Survey().has_passed_closing(today())
    assert not Survey(closes_on=today()).has_passed_closing(today())
    assert Survey(closes_on=days(-1)).has_passed_closing(today())


def test_pause_and_resume_set_the_status():
    survey = Survey(status=SurveyStatus.PUBLISHED)
    survey.pause()
    assert survey.status == SurveyStatus.PAUSED
    survey.resume()
    assert survey.status == SurveyStatus.PUBLISHED


# --- Settings and their checks -----------------------------------------------------------


def test_create_stores_the_three_settings(service, provider):
    survey = service.create_survey(
        provider, "Dated", "", opens_on=days(1), closes_on=days(10), target_responses=50
    )

    survey.refresh_from_db()
    assert (survey.opens_on, survey.closes_on, survey.target_responses) == (
        days(1),
        days(10),
        50,
    )


def test_create_without_settings_leaves_them_empty(service, provider):
    survey = service.create_survey(provider, "Plain", "")

    assert (survey.opens_on, survey.closes_on, survey.target_responses) == (None, None, None)


def test_update_stores_and_clears_the_settings(service, provider):
    survey = service.create_survey(provider, "Dated", "", closes_on=days(5), target_responses=5)

    service.update_survey(
        provider, survey.survey_id, "Dated", "", opens_on=days(2), closes_on=days(3)
    )

    survey.refresh_from_db()
    assert (survey.opens_on, survey.closes_on, survey.target_responses) == (
        days(2),
        days(3),
        None,
    )


@pytest.mark.parametrize(
    "values, message",
    [
        (
            {"opens_on": days(5), "closes_on": days(4)},
            "The opening date must be on or before the closing date.",
        ),
        ({"closes_on": days(-1)}, "The closing date cannot be in the past."),
        ({"target_responses": 4}, "The response limit must be at least 5."),
        ({"target_responses": 0}, "The response limit must be at least 5."),
        ({"target_responses": True}, "The response limit must be at least 5."),
        ({"target_responses": "10"}, "The response limit must be at least 5."),
        ({"target_responses": 10001}, "The response limit must be 10,000 or fewer."),
    ],
)
def test_create_and_update_refuse_bad_settings(service, provider, values, message):
    with pytest.raises(ValidationError, match=message):
        service.create_survey(provider, "Bad", "", **values)

    draft = service.create_survey(provider, "Draft", "")
    with pytest.raises(ValidationError, match=message):
        service.update_survey(provider, draft.survey_id, "Draft", "", **values)


@pytest.mark.parametrize(
    "values",
    [
        {"opens_on": days(3), "closes_on": days(3)},
        {"closes_on": today()},
        {"opens_on": days(-5)},
        {"target_responses": 5},
        {"target_responses": 10000},
    ],
)
def test_create_accepts_boundary_settings(service, provider, values):
    assert service.create_survey(provider, "Edge", "", **values).survey_id


def test_a_draft_whose_closing_date_passed_cannot_be_submitted(service, provider):
    draft = make_survey(provider, status=SurveyStatus.DRAFT)
    Survey.objects.filter(pk=draft.pk).update(closes_on=days(-1))

    with pytest.raises(ValidationError, match="The closing date cannot be in the past."):
        service.submit_for_review(provider, draft.survey_id)

    draft.refresh_from_db()
    assert draft.status == SurveyStatus.DRAFT


def test_a_draft_with_a_future_closing_date_can_be_submitted(service, provider):
    draft = make_survey(provider, status=SurveyStatus.DRAFT, closes_on=days(2))

    service.submit_for_review(provider, draft.survey_id)

    draft.refresh_from_db()
    assert draft.status == SurveyStatus.PENDING_REVIEW


# --- Closing date reached ----------------------------------------------------------------


def test_close_past_end_closes_published_and_paused_surveys_past_their_date(provider):
    published = make_survey(provider, closes_on=days(-1))
    paused = make_survey(provider, status=SurveyStatus.PAUSED, closes_on=days(-3))
    closing_today = make_survey(provider, closes_on=today())
    no_date = make_survey(provider)
    draft = make_survey(provider, status=SurveyStatus.DRAFT, closes_on=days(-1))

    closed = SurveyRepository().close_past_end(today())

    assert closed == 2
    for survey in (published, paused):
        survey.refresh_from_db()
        assert survey.status == SurveyStatus.CLOSED
        assert survey.closed_at is not None
    for survey, status in (
        (closing_today, SurveyStatus.PUBLISHED),
        (no_date, SurveyStatus.PUBLISHED),
        (draft, SurveyStatus.DRAFT),
    ):
        survey.refresh_from_db()
        assert survey.status == status
        assert survey.closed_at is None


def test_the_provider_list_closes_a_survey_past_its_date(service, provider):
    survey = make_survey(provider, closes_on=days(-1))

    items = service.list_provider_survey_items(provider)

    assert items[0]["survey"].status == SurveyStatus.CLOSED
    assert items[0]["can_view_analytics"] is True


def test_list_provider_surveys_closes_a_survey_past_its_date(service, provider):
    make_survey(provider, closes_on=days(-1))

    (survey,) = service.list_provider_surveys(provider)

    assert survey.status == SurveyStatus.CLOSED


def test_the_system_report_counts_a_survey_past_its_date_as_closed(provider):
    make_survey(provider, closes_on=days(-1))
    make_survey(provider, status=SurveyStatus.PAUSED)

    report = AdminService().generate_system_report(create_admin(), today(), today())

    assert report["surveys_by_status"][SurveyStatus.CLOSED.value] == 1
    assert report["surveys_by_status"][SurveyStatus.PAUSED.value] == 1


def test_approval_is_refused_after_the_closing_date(provider):
    survey = make_survey(provider, status=SurveyStatus.PENDING_REVIEW, closes_on=days(-1))

    with pytest.raises(
        ValidationError,
        match="The closing date has passed. Reject the survey so the provider can change it.",
    ):
        SurveyReviewService().approve(create_admin(), survey.survey_id)

    survey.refresh_from_db()
    assert survey.status == SurveyStatus.PENDING_REVIEW


def test_approval_on_the_closing_day_publishes(provider):
    survey = make_survey(provider, status=SurveyStatus.PENDING_REVIEW, closes_on=today())

    approved = SurveyReviewService().approve(create_admin(), survey.survey_id)

    assert approved.status == SurveyStatus.PUBLISHED


# --- Pause, resume, close ----------------------------------------------------------------


def test_pause_and_resume_a_published_survey(service, provider):
    survey = make_survey(provider)

    assert service.pause_survey(provider, survey.survey_id).status == SurveyStatus.PAUSED
    assert service.resume_survey(provider, survey.survey_id).status == SurveyStatus.PUBLISHED


@pytest.mark.parametrize(
    "status",
    [SurveyStatus.DRAFT, SurveyStatus.PENDING_REVIEW, SurveyStatus.PAUSED, SurveyStatus.CLOSED],
)
def test_only_published_surveys_can_be_paused(service, provider, status):
    survey = make_survey(provider, status=status)

    with pytest.raises(NotEditable, match="Only published surveys can be paused."):
        service.pause_survey(provider, survey.survey_id)


@pytest.mark.parametrize(
    "status",
    [
        SurveyStatus.DRAFT,
        SurveyStatus.PENDING_REVIEW,
        SurveyStatus.PUBLISHED,
        SurveyStatus.CLOSED,
    ],
)
def test_only_paused_surveys_can_be_resumed(service, provider, status):
    survey = make_survey(provider, status=status)

    with pytest.raises(NotEditable, match="Only paused surveys can be resumed."):
        service.resume_survey(provider, survey.survey_id)


@pytest.mark.parametrize("status", [SurveyStatus.PUBLISHED, SurveyStatus.PAUSED])
def test_published_and_paused_surveys_can_be_closed(service, provider, status):
    survey = make_survey(provider, status=status)

    closed = service.close_survey(provider, survey.survey_id)

    assert closed.status == SurveyStatus.CLOSED
    assert closed.closed_at is not None


@pytest.mark.parametrize(
    "status", [SurveyStatus.DRAFT, SurveyStatus.PENDING_REVIEW, SurveyStatus.CLOSED]
)
def test_other_states_cannot_be_closed(service, provider, status):
    survey = make_survey(provider, status=status)

    with pytest.raises(NotEditable, match="Only published or paused surveys can be closed."):
        service.close_survey(provider, survey.survey_id)


def test_pause_and_resume_need_the_owner(service, provider):
    survey = make_survey(provider)
    other = make_user(UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        service.pause_survey(other, survey.survey_id)
    with pytest.raises(UnauthorizedAction):
        service.resume_survey(other, survey.survey_id)


def test_paused_survey_action_flags(service, provider):
    make_survey(provider, status=SurveyStatus.PAUSED)

    (item,) = service.list_provider_survey_items(provider)

    assert item["can_pause"] is False
    assert item["can_resume"] is True
    assert item["can_close"] is True
    assert item["can_view_analytics"] is True
    assert item["can_edit"] is False
    assert item["can_delete"] is False


# --- The respondent's list ---------------------------------------------------------------


def test_eligible_item_has_closes_on_and_published_on_is_the_later_date(service, provider):
    respondent = make_respondent()
    survey = make_survey(provider, opens_on=days(-1), closes_on=days(9))
    Survey.objects.filter(pk=survey.pk).update(
        published_at=timezone.now() - datetime.timedelta(days=4)
    )

    (item,) = service.get_eligible_survey_items(respondent)

    assert item["closes_on"] == days(9)
    assert item["published_on"] == days(-1)


def test_published_on_is_the_publish_day_when_it_is_later(service, provider):
    respondent = make_respondent()
    survey = make_survey(provider, opens_on=days(-6))
    Survey.objects.filter(pk=survey.pk).update(published_at=timezone.now())

    (item,) = service.get_eligible_survey_items(respondent)

    assert item["published_on"] == today()
    assert item["closes_on"] is None


def test_published_on_is_the_opening_date_without_a_publish_time(service, provider):
    respondent = make_respondent()
    make_survey(provider, opens_on=today())

    (item,) = service.get_eligible_survey_items(respondent)

    assert item["published_on"] == today()


# --- Answering ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, fields, message",
    [
        (SurveyStatus.PAUSED, {}, "This survey is paused."),
        (SurveyStatus.CLOSED, {}, "This survey has closed."),
        (SurveyStatus.DRAFT, {}, "Responses are allowed only for published surveys."),
        (
            SurveyStatus.PENDING_REVIEW,
            {},
            "Responses are allowed only for published surveys.",
        ),
        (SurveyStatus.PUBLISHED, {"opens_on": days(1)}, "This survey is not open yet."),
        (SurveyStatus.PUBLISHED, {"closes_on": days(-1)}, "This survey has closed."),
    ],
)
def test_ensure_can_answer_names_the_reason(provider, status, fields, message):
    respondent = make_respondent()
    survey = make_survey(provider, status=status, **fields)

    with pytest.raises(NotEditable, match=message):
        ResponseService().ensure_can_answer(respondent, survey.survey_id)


def test_a_survey_open_from_today_until_today_can_be_answered(provider):
    respondent = make_respondent()
    survey = make_survey(provider, opens_on=today(), closes_on=today())

    assert ResponseService().ensure_can_answer(respondent, survey.survey_id) == survey


def test_a_paused_survey_keeps_no_new_draft(provider):
    respondent = make_respondent()
    survey = make_survey(provider, status=SurveyStatus.PAUSED)
    question = survey.questions.get()

    with pytest.raises(NotEditable, match="This survey is paused."):
        ResponseService().save_draft(
            respondent,
            survey.survey_id,
            [{"question_id": question.question_id, "rating_value": 3}],
        )

    assert not ResponseDraft.objects.filter(survey=survey).exists()
