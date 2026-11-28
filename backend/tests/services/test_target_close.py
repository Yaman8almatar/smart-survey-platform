"""FR-11: the response that reaches the limit closes the survey, under a row lock."""

import datetime
from itertools import count

import pytest
from django.utils import timezone

from apps.core.models import (
    Question,
    RespondentProfile,
    Response,
    ResponseDraft,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import NotEditable
from repositories.survey_repository import SurveyRepository
from services.response_service import ResponseService

pytestmark = pytest.mark.django_db

_numbers = count(1)


def days(n):
    return timezone.localdate() + datetime.timedelta(days=n)


def make_user(user_type):
    return User.objects.create_user(
        email=f"target-{next(_numbers)}@example.com",
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


def make_survey(status=SurveyStatus.PUBLISHED, **fields):
    survey = Survey.objects.create(
        provider=make_user(UserType.SERVICE_PROVIDER),
        title="Limited survey",
        status=status,
        **fields,
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


def add_responses(survey, number, excluded=0):
    for index in range(number):
        Response.objects.create(
            survey=survey, respondent=make_respondent(), is_excluded=index < excluded
        )


def answers(survey):
    return [{"question_id": survey.questions.get().question_id, "rating_value": 4}]


def submit(survey, respondent=None, service=None):
    return (service or ResponseService()).submit_response(
        respondent or make_respondent(), survey.survey_id, answers(survey)
    )


def test_the_response_that_reaches_the_limit_is_stored_and_closes_the_survey():
    survey = make_survey(target_responses=5)
    add_responses(survey, 4)

    response = submit(survey)

    assert Response.objects.filter(pk=response.pk).exists()
    survey.refresh_from_db()
    assert survey.status == SurveyStatus.CLOSED
    assert survey.closed_at is not None
    assert Response.objects.filter(survey=survey).count() == 5


def test_a_response_under_the_limit_keeps_the_survey_open():
    survey = make_survey(target_responses=5)
    add_responses(survey, 3)

    submit(survey)

    survey.refresh_from_db()
    assert survey.status == SurveyStatus.PUBLISHED
    assert survey.closed_at is None


def test_after_the_limit_the_next_respondent_is_told_it_has_closed():
    survey = make_survey(target_responses=5)
    add_responses(survey, 4)
    submit(survey)
    late = make_respondent()

    with pytest.raises(NotEditable, match="This survey has closed."):
        submit(survey, late)

    assert not Response.objects.filter(survey=survey, respondent=late).exists()
    assert Response.objects.filter(survey=survey).count() == 5


def test_a_full_survey_still_published_refuses_inside_the_lock():
    # The count inside the lock is what holds: the survey is still PUBLISHED here.
    survey = make_survey(target_responses=5)
    add_responses(survey, 5)
    late = make_respondent()

    with pytest.raises(NotEditable, match="This survey has closed."):
        submit(survey, late)

    assert not Response.objects.filter(survey=survey, respondent=late).exists()


def test_an_excluded_response_still_counts_toward_the_limit():
    survey = make_survey(target_responses=5)
    add_responses(survey, 4, excluded=1)

    submit(survey)

    survey.refresh_from_db()
    assert survey.status == SurveyStatus.CLOSED


def test_without_a_limit_the_survey_stays_open():
    survey = make_survey()
    add_responses(survey, 6)

    submit(survey)

    survey.refresh_from_db()
    assert survey.status == SurveyStatus.PUBLISHED


class SpySurveyRepository(SurveyRepository):
    def __init__(self):
        self.locked_reads = []

    def find_by_id_for_update(self, survey_id):
        self.locked_reads.append(survey_id)
        return super().find_by_id_for_update(survey_id)


def test_submit_reads_the_survey_with_its_row_locked():
    survey = make_survey(target_responses=5)
    spy = SpySurveyRepository()

    submit(survey, service=ResponseService(survey_repository=spy))

    assert spy.locked_reads == [survey.survey_id]


def test_submit_rechecks_the_state_inside_the_lock():
    # The survey is paused between the first check and the locked read.
    survey = make_survey()

    class PausingRepository(SurveyRepository):
        def find_by_id_for_update(self, survey_id):
            Survey.objects.filter(pk=survey_id).update(status=SurveyStatus.PAUSED)
            return super().find_by_id_for_update(survey_id)

    respondent = make_respondent()
    with pytest.raises(NotEditable, match="This survey is paused."):
        submit(survey, respondent, ResponseService(survey_repository=PausingRepository()))

    assert not Response.objects.filter(survey=survey).exists()


@pytest.mark.parametrize(
    "status, fields, message",
    [
        (SurveyStatus.PAUSED, {}, "This survey is paused."),
        (SurveyStatus.PUBLISHED, {"opens_on": days(1)}, "This survey is not open yet."),
        (SurveyStatus.PUBLISHED, {"closes_on": days(-1)}, "This survey has closed."),
    ],
)
def test_a_survey_not_taking_responses_refuses_the_draft_and_the_submit(
    status, fields, message
):
    survey = make_survey(status=status, **fields)
    respondent = make_respondent()
    service = ResponseService()

    with pytest.raises(NotEditable, match=message):
        service.save_draft(respondent, survey.survey_id, answers(survey))
    with pytest.raises(NotEditable, match=message):
        service.submit_response(respondent, survey.survey_id, answers(survey))

    assert not ResponseDraft.objects.filter(survey=survey).exists()
    assert not Response.objects.filter(survey=survey).exists()
