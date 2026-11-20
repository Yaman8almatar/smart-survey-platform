"""TASK-49 (FR-07, board W-07): QualityService excludes or includes one response by its number.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import itertools

import pytest

from apps.core.models import Response, ResponseQuality, Survey, User
from core.enums import AccountStatus, SurveyStatus, UserType
from core.exceptions import ResponseNotFound, UnauthorizedAction, ValidationError
from repositories.response_repository import ResponseRepository
from services.quality_service import QualityService

pytestmark = pytest.mark.django_db

BEFORE_CHECKS_MESSAGE = (
    "This response was collected before quality checks. It has no score and stays included."
)
_emails = itertools.count()


def make_user(user_type):
    return User.objects.create_user(
        email=f"single-inclusion-{next(_emails)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return make_user(UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    return Survey.objects.create(provider=provider, title="Single", status=SurveyStatus.PUBLISHED)


def add_response(survey, evidence=True, excluded=False):
    response = Response.objects.create(
        survey=survey, respondent=make_user(UserType.RESPONDENT), is_excluded=excluded
    )
    if evidence:
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=[],
            active_ms=None,
            signals_ok=False,
        )
    return response


def states(survey):
    return list(
        Response.objects.filter(survey=survey)
        .order_by("response_id")
        .values_list("is_excluded", flat=True)
    )


def test_find_by_number_returns_the_response_at_that_position(survey):
    first = add_response(survey)
    second = add_response(survey, evidence=False)

    repository = ResponseRepository()

    assert repository.find_by_number(survey.survey_id, 1) == {
        "response_id": first.response_id,
        "has_evidence": True,
    }
    assert repository.find_by_number(survey.survey_id, 2) == {
        "response_id": second.response_id,
        "has_evidence": False,
    }
    assert repository.find_by_number(survey.survey_id, 0) is None
    assert repository.find_by_number(survey.survey_id, 3) is None


def test_exclude_by_number_returns_1_then_0(provider, survey):
    responses = [add_response(survey) for _ in range(5)]
    service = QualityService()

    assert service.set_response_inclusion(provider, survey.survey_id, 2, True) == 1
    assert service.set_response_inclusion(provider, survey.survey_id, 2, True) == 0

    responses[1].refresh_from_db()
    assert responses[1].is_excluded is True
    assert responses[1].excluded_at is not None
    assert states(survey) == [False, True, False, False, False]


def test_include_again(provider, survey):
    responses = [add_response(survey) for _ in range(5)]
    service = QualityService()
    service.set_response_inclusion(provider, survey.survey_id, 3, True)

    assert service.set_response_inclusion(provider, survey.survey_id, 3, False) == 1
    assert service.set_response_inclusion(provider, survey.survey_id, 3, False) == 0

    responses[2].refresh_from_db()
    assert responses[2].is_excluded is False
    assert responses[2].excluded_at is None


def test_the_included_count_follows_at_once(provider, survey):
    for _ in range(5):
        add_response(survey)
    service = QualityService()

    service.set_response_inclusion(provider, survey.survey_id, 1, True)
    assert service.evaluate_survey(provider, survey.survey_id)["included_count"] == 4

    service.set_response_inclusion(provider, survey.survey_id, 1, False)
    assert service.evaluate_survey(provider, survey.survey_id)["included_count"] == 5


def test_a_response_before_quality_checks_cannot_be_excluded(provider, survey):
    for _ in range(4):
        add_response(survey)
    add_response(survey, evidence=False)

    with pytest.raises(ValidationError, match=BEFORE_CHECKS_MESSAGE):
        QualityService().set_response_inclusion(provider, survey.survey_id, 5, True)

    assert states(survey) == [False] * 5


def test_a_response_before_quality_checks_can_be_included_again(provider, survey):
    for _ in range(4):
        add_response(survey)
    add_response(survey, evidence=False, excluded=True)

    assert QualityService().set_response_inclusion(provider, survey.survey_id, 5, False) == 1
    assert states(survey) == [False] * 5


def test_locked_results_refuse_the_change(provider, survey):
    for _ in range(4):
        add_response(survey)

    with pytest.raises(ValidationError, match="Results open at 5 responses."):
        QualityService().set_response_inclusion(provider, survey.survey_id, 1, True)

    assert states(survey) == [False] * 4


def test_another_provider_is_refused(survey):
    for _ in range(5):
        add_response(survey)
    other = make_user(UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        QualityService().set_response_inclusion(other, survey.survey_id, 1, True)

    assert states(survey) == [False] * 5


@pytest.mark.parametrize("number", [0, 6])
def test_numbers_outside_the_survey_are_refused(provider, survey, number):
    for _ in range(5):
        add_response(survey)

    with pytest.raises(ResponseNotFound, match="Response does not belong to this survey."):
        QualityService().set_response_inclusion(provider, survey.survey_id, number, True)

    assert states(survey) == [False] * 5


def test_excluded_must_be_a_bool(provider, survey):
    for _ in range(5):
        add_response(survey)

    with pytest.raises(ValidationError, match="Excluded must be true or false."):
        QualityService().set_response_inclusion(provider, survey.survey_id, 1, "yes")

    assert states(survey) == [False] * 5
