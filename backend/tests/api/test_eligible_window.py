"""FR-11: the app lists only surveys open today, and each row carries its closing date."""

import datetime

import pytest
from django.utils import timezone

from apps.core.models import Survey
from core.enums import SurveyStatus

pytestmark = pytest.mark.django_db

ELIGIBLE_URL = "/api/v1/surveys/eligible/"


def days(n):
    return timezone.localdate() + datetime.timedelta(days=n)


def listed_titles(client, authenticate, respondent):
    authenticate(respondent)
    return [row["title"] for row in client.get(ELIGIBLE_URL).json()]


def test_surveys_not_open_yet_past_closing_or_paused_are_not_listed(
    client, authenticate, respondent, make_survey
):
    Survey.objects.filter(pk=make_survey(title="Not yet").pk).update(opens_on=days(1))
    Survey.objects.filter(pk=make_survey(title="Past").pk).update(closes_on=days(-1))
    make_survey(title="Paused", status=SurveyStatus.PAUSED)
    make_survey(title="Open")

    assert listed_titles(client, authenticate, respondent) == ["Open"]


def test_surveys_opening_and_closing_today_are_listed(
    client, authenticate, respondent, make_survey
):
    Survey.objects.filter(pk=make_survey(title="Opens today").pk).update(opens_on=days(0))
    Survey.objects.filter(pk=make_survey(title="Closes today").pk).update(closes_on=days(0))

    assert sorted(listed_titles(client, authenticate, respondent)) == [
        "Closes today",
        "Opens today",
    ]


def test_the_row_has_closes_on(client, authenticate, respondent, survey):
    Survey.objects.filter(pk=survey.pk).update(closes_on=days(10))
    authenticate(respondent)

    (row,) = client.get(ELIGIBLE_URL).json()

    assert row["closes_on"] == days(10).isoformat()


def test_a_paused_survey_refuses_the_form(client, authenticate, respondent, survey):
    Survey.objects.filter(pk=survey.pk).update(status=SurveyStatus.PAUSED)
    authenticate(respondent)

    response = client.get(f"/api/v1/surveys/{survey.survey_id}/")

    assert response.status_code != 200
    assert "This survey is paused." in response.content.decode()
