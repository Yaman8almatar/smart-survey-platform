import datetime

import pytest
from django.utils import timezone

from apps.core.models import (
    Question,
    RespondentProfile,
    Response,
    ResponseQuality,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from services.survey_service import SurveyService

pytestmark = pytest.mark.django_db

NOW = timezone.now()


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return create_user("provider-ranking@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def respondent():
    user = create_user("respondent-ranking@example.com", UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=user,
        age=30,
        gender=Gender.FEMALE,
        region="DAMASCUS",
        interests=["TECHNOLOGY", "SPORTS", "HEALTH"],
    )
    return user


def published_survey(provider, title, interests=(), days_ago=0, question_types=()):
    survey = Survey.objects.create(
        provider=provider,
        title=title,
        description="Description",
        status=SurveyStatus.PUBLISHED,
        published_at=NOW - datetime.timedelta(days=days_ago),
    )
    TargetingCriteria.objects.create(survey=survey, interests=list(interests))
    for index, question_type in enumerate(question_types):
        Question.objects.create(
            survey=survey,
            question_text=f"Question {index}",
            question_type=question_type,
            is_required=False,
            order_index=index,
        )
    return survey


def add_evidence(survey, count, active_ms, signals_ok=True):
    for _ in range(count):
        index = User.objects.count()
        other = create_user(f"evidence-{index}@example.com", UserType.RESPONDENT)
        response = Response.objects.create(survey=survey, respondent=other)
        ResponseQuality.objects.create(
            response=response, survey=survey, active_ms=active_ms, signals_ok=signals_ok
        )


def eligible_titles(respondent):
    return [item["survey"].title for item in SurveyService().get_eligible_survey_items(respondent)]


def test_more_shared_interests_come_first_whatever_the_date(provider, respondent):
    published_survey(provider, "None shared", interests=(), days_ago=0)
    published_survey(provider, "One shared", interests=("SPORTS", "FOOD"), days_ago=1)
    published_survey(provider, "Two shared", interests=("TECHNOLOGY", "HEALTH"), days_ago=5)

    assert eligible_titles(respondent) == ["Two shared", "One shared", "None shared"]


def test_equal_shared_interests_keep_newest_first(provider, respondent):
    published_survey(provider, "Older", interests=("SPORTS",), days_ago=3)
    published_survey(provider, "Newest", interests=("HEALTH",), days_ago=0)
    published_survey(provider, "Middle", interests=("TECHNOLOGY",), days_ago=1)

    assert eligible_titles(respondent) == ["Newest", "Middle", "Older"]


def test_expected_minutes_use_the_estimate_without_enough_valid_responses(provider, respondent):
    survey = published_survey(
        provider,
        "Estimate",
        question_types=[QuestionType.OPEN_TEXT] * 2 + [QuestionType.MULTIPLE_CHOICE],
    )
    add_evidence(survey, 19, 600_000)

    (item,) = SurveyService().get_eligible_survey_items(respondent)

    # 2 * 40 + 10 = 90 seconds.
    assert item["expected_minutes"] == 2


def test_expected_minutes_use_the_median_of_twenty_valid_responses(provider, respondent):
    survey = published_survey(provider, "Median", question_types=[QuestionType.RATING_SCALE])
    add_evidence(survey, 20, 125_000)
    # Neither an invalid row nor one without an active time counts.
    add_evidence(survey, 1, 3_600_000, signals_ok=False)
    add_evidence(survey, 1, None)

    (item,) = SurveyService().get_eligible_survey_items(respondent)

    assert item["expected_minutes"] == 3


def test_published_on_is_the_local_date_of_publishing(provider, respondent):
    survey = published_survey(provider, "Dated", days_ago=2)

    (item,) = SurveyService().get_eligible_survey_items(respondent)

    assert isinstance(item["published_on"], datetime.date)
    assert item["published_on"] == timezone.localdate(survey.published_at)


def test_published_on_is_none_without_a_publish_time(provider, respondent):
    survey = published_survey(provider, "Undated")
    Survey.objects.filter(pk=survey.pk).update(published_at=None)

    (item,) = SurveyService().get_eligible_survey_items(respondent)

    assert item["published_on"] is None
