"""FR-10 Part A: the invitation link of a survey and the token the app turns into a survey id."""

import pytest

from apps.core.models import RespondentProfile, Survey, User
from core.enums import AccountStatus, Gender, SurveyStatus, UserType
from core.exceptions import InvitationNotFound, NotEditable, UnauthorizedAction
from repositories.survey_repository import SurveyRepository
from services.survey_service import SurveyService

pytestmark = pytest.mark.django_db

SHAREABLE = (SurveyStatus.PUBLISHED, SurveyStatus.PAUSED, SurveyStatus.CLOSED)
NOT_SHAREABLE = (SurveyStatus.DRAFT, SurveyStatus.PENDING_REVIEW)


def _make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return _make_user("provider@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def respondent():
    return _make_user("respondent@example.com", UserType.RESPONDENT)


@pytest.fixture
def make_survey(provider):
    def _make_survey(status=SurveyStatus.PUBLISHED, owner=None):
        return Survey.objects.create(
            provider=owner or provider, title="Campus survey", status=status
        )

    return _make_survey


def _stored_token(survey):
    survey.refresh_from_db()
    return survey.invite_token


def test_token_has_22_characters_and_is_stable(provider, make_survey):
    survey = make_survey()
    service = SurveyService()

    first = service.get_invitation(provider, survey.survey_id)
    second = service.get_invitation(provider, survey.survey_id)

    token = _stored_token(survey)
    assert len(token) == 22
    assert first["survey"].invite_token == token
    assert first["link"] == second["link"]
    assert first["link"].endswith(f"/?invite={token}")


def test_link_uses_the_app_public_url_setting(settings, provider, make_survey):
    settings.APP_PUBLIC_URL = "https://app.example.com"
    survey = make_survey()

    result = SurveyService().get_invitation(provider, survey.survey_id)

    assert result["link"] == f"https://app.example.com/?invite={_stored_token(survey)}"


@pytest.mark.parametrize("status", NOT_SHAREABLE)
def test_draft_and_pending_raise_not_editable_and_store_nothing(provider, make_survey, status):
    survey = make_survey(status)

    with pytest.raises(NotEditable, match="available once the survey is published"):
        SurveyService().get_invitation(provider, survey.survey_id)

    assert _stored_token(survey) is None


def test_another_providers_survey_is_refused_and_stores_nothing(make_survey):
    other = _make_user("other@example.com", UserType.SERVICE_PROVIDER)
    survey = make_survey(owner=other)
    provider = User.objects.get(email="provider@example.com")

    with pytest.raises(UnauthorizedAction):
        SurveyService().get_invitation(provider, survey.survey_id)

    assert _stored_token(survey) is None


@pytest.mark.parametrize("user_type", (UserType.RESPONDENT, UserType.ADMIN))
def test_other_roles_calling_get_invitation_leave_the_token_null(make_survey, user_type):
    survey = make_survey()
    user = _make_user(f"{user_type.lower()}@example.org", user_type)

    with pytest.raises(UnauthorizedAction):
        SurveyService().get_invitation(user, survey.survey_id)

    assert _stored_token(survey) is None


def test_set_invite_token_if_empty_keeps_the_first_token(make_survey):
    survey = make_survey()
    repository = SurveyRepository()

    assert repository.set_invite_token_if_empty(survey.survey_id, "first-token") == "first-token"
    assert repository.set_invite_token_if_empty(survey.survey_id, "second-token") == "first-token"
    assert _stored_token(survey) == "first-token"


@pytest.mark.parametrize("status", SHAREABLE)
def test_resolve_returns_the_survey_id_for_shareable_states(
    provider, respondent, make_survey, status
):
    survey = make_survey()
    token = SurveyService().get_invitation(provider, survey.survey_id)["survey"].invite_token
    Survey.objects.filter(survey_id=survey.survey_id).update(status=status)

    result = SurveyService().resolve_invitation(respondent, token)

    assert result == {"survey_id": survey.survey_id, "profile_complete": False}


def test_profile_complete_follows_the_respondent_profile(provider, respondent, make_survey):
    survey = make_survey()
    service = SurveyService()
    token = service.get_invitation(provider, survey.survey_id)["survey"].invite_token

    assert service.resolve_invitation(respondent, token)["profile_complete"] is False

    profile = RespondentProfile.objects.create(
        user=respondent, age=30, gender=Gender.MALE, region="DAMASCUS", interests=[]
    )
    assert service.resolve_invitation(respondent, token)["profile_complete"] is False

    profile.interests = ["SPORTS"]
    profile.save()
    assert service.resolve_invitation(respondent, token)["profile_complete"] is True


@pytest.mark.parametrize("token", ("no-such-token", "x" * 40, ""))
def test_unknown_or_too_long_token_is_not_found(respondent, token):
    with pytest.raises(InvitationNotFound, match="This invitation link is not valid."):
        SurveyService().resolve_invitation(respondent, token)


def test_token_on_a_draft_is_not_found(respondent, make_survey):
    survey = make_survey(SurveyStatus.DRAFT)
    Survey.objects.filter(survey_id=survey.survey_id).update(invite_token="hand-set-token")

    with pytest.raises(InvitationNotFound):
        SurveyService().resolve_invitation(respondent, "hand-set-token")


@pytest.mark.parametrize("user_type", (UserType.SERVICE_PROVIDER, UserType.ADMIN))
def test_other_roles_cannot_resolve(provider, make_survey, user_type):
    survey = make_survey()
    token = SurveyService().get_invitation(provider, survey.survey_id)["survey"].invite_token
    user = provider if user_type == UserType.SERVICE_PROVIDER else _make_user(
        "admin@example.com", UserType.ADMIN
    )

    with pytest.raises(UnauthorizedAction):
        SurveyService().resolve_invitation(user, token)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (SurveyStatus.DRAFT, False),
        (SurveyStatus.PENDING_REVIEW, False),
        (SurveyStatus.PUBLISHED, True),
        (SurveyStatus.PAUSED, True),
        (SurveyStatus.CLOSED, True),
    ],
)
def test_can_share_flag_per_state(provider, make_survey, status, expected):
    make_survey(status)

    [item] = SurveyService().list_provider_survey_items(provider)

    assert item["can_share"] is expected
