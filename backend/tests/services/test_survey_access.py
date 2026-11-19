"""TASK-43 rider 2: one owner check for AnalysisService and QualityService (D-191 (2))."""

import pytest

from apps.core.models import Survey, User
from core.enums import AccountStatus, UserType
from core.exceptions import SurveyNotFound, UnauthorizedAction
from repositories.survey_repository import SurveyRepository
from services.analysis_service import AnalysisService
from services.quality_service import QualityService
from services.survey_access import ensure_survey_owner

pytestmark = pytest.mark.django_db

NOT_PROVIDER = "^Only service providers can view survey analytics.$"
NOT_FOUND = "^Survey not found.$"
NOT_OWNER = "^Only the survey owner can view survey analytics.$"


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def owner():
    return make_user("owner-access@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(owner):
    return Survey.objects.create(provider=owner, title="Access")


def test_helper_returns_the_survey_of_its_owner(owner, survey):
    assert ensure_survey_owner(SurveyRepository(), owner, survey.survey_id) == survey


def test_helper_refuses_a_user_who_is_not_a_provider(survey):
    respondent = make_user("respondent-access@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction, match=NOT_PROVIDER):
        ensure_survey_owner(SurveyRepository(), respondent, survey.survey_id)


def test_helper_refuses_a_missing_survey(owner):
    with pytest.raises(SurveyNotFound, match=NOT_FOUND):
        ensure_survey_owner(SurveyRepository(), owner, 999_999)


def test_helper_refuses_another_provider(survey):
    other = make_user("other-access@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction, match=NOT_OWNER):
        ensure_survey_owner(SurveyRepository(), other, survey.survey_id)


@pytest.mark.parametrize(
    "call",
    [
        lambda user, survey_id: AnalysisService(analyzer=object()).get_survey_results(
            user, survey_id
        ),
        lambda user, survey_id: AnalysisService(analyzer=object()).retry_failed(user, survey_id),
        lambda user, survey_id: QualityService().evaluate_survey(user, survey_id),
        lambda user, survey_id: QualityService().include_all(user, survey_id),
        lambda user, survey_id: QualityService().set_inclusion(user, survey_id, [], True),
    ],
)
def test_both_services_give_the_same_messages(survey, call):
    respondent = make_user("respondent-same@example.com", UserType.RESPONDENT)
    other = make_user("other-same@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction, match=NOT_PROVIDER):
        call(respondent, survey.survey_id)
    with pytest.raises(SurveyNotFound, match=NOT_FOUND):
        call(other, 999_999)
    with pytest.raises(UnauthorizedAction, match=NOT_OWNER):
        call(other, survey.survey_id)
