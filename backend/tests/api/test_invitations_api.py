"""FR-10 Part A: GET /api/v1/invitations/<token>/ turns an invitation token into a survey id."""

import pytest

from apps.core.models import Survey
from core.enums import SurveyStatus
from services.survey_service import SurveyService

pytestmark = pytest.mark.django_db


def _url(token):
    return f"/api/v1/invitations/{token}/"


def _token_of(provider, survey):
    return SurveyService().get_invitation(provider, survey.survey_id)["survey"].invite_token


def test_respondent_gets_exactly_the_survey_id_and_profile_completeness(
    authenticate, respondent, provider, survey
):
    token = _token_of(provider, survey)

    response = authenticate(respondent).get(_url(token))

    assert response.status_code == 200
    assert response.json() == {"survey_id": survey.survey_id, "profile_complete": True}


def test_anonymous_gets_401(client, provider, survey):
    token = _token_of(provider, survey)

    response = client.get(_url(token))

    assert response.status_code == 401
    assert "error" in response.json()


def test_provider_gets_403(authenticate, provider, survey):
    token = _token_of(provider, survey)

    response = authenticate(provider).get(_url(token))

    assert response.status_code == 403


def test_unknown_token_gets_404_invitation_not_found(authenticate, respondent):
    response = authenticate(respondent).get(_url("no-such-token"))

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "invitation_not_found",
            "message": "This invitation link is not valid.",
        }
    }


def test_draft_with_a_token_gets_404(authenticate, respondent, make_survey):
    draft = make_survey(status=SurveyStatus.DRAFT)
    Survey.objects.filter(survey_id=draft.survey_id).update(invite_token="hand-set-token")

    response = authenticate(respondent).get(_url("hand-set-token"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invitation_not_found"


def test_respondent_outside_the_targeting_resolves_but_cannot_open_the_survey(
    authenticate, respondent, provider, make_survey
):
    targeted = make_survey(regions=["ALEPPO"])
    token = _token_of(provider, targeted)
    client = authenticate(respondent)

    resolved = client.get(_url(token))
    detail = client.get(f"/api/v1/surveys/{targeted.survey_id}/")

    assert resolved.status_code == 200
    assert resolved.json()["survey_id"] == targeted.survey_id
    assert detail.status_code == 403
