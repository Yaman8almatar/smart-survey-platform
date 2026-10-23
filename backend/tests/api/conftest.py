import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import (
    AccountStatus,
    Gender,
    QuestionType,
    SurveyStatus,
    UserType,
)

PASSWORD = "strong-password"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def make_user():
    def _make_user(email, user_type, account_status=AccountStatus.ACTIVE):
        user = User.objects.create_user(
            email=email,
            password=PASSWORD,
            name="Test User",
            user_type=user_type,
            account_status=account_status,
        )
        if account_status != AccountStatus.ACTIVE:
            user.is_active = False
            user.save()
        return user

    return _make_user


@pytest.fixture
def make_respondent(make_user):
    def _make_respondent(
        email="respondent@example.com",
        age=30,
        gender=Gender.MALE,
        region="Damascus",
        interests="sports",
        account_status=AccountStatus.ACTIVE,
    ):
        user = make_user(email, UserType.RESPONDENT, account_status)
        RespondentProfile.objects.create(
            user=user,
            age=age,
            gender=gender,
            region=region,
            interests=interests,
        )
        return user

    return _make_respondent


@pytest.fixture
def respondent(make_respondent):
    return make_respondent()


@pytest.fixture
def provider(make_user):
    return make_user("provider@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def admin(make_user):
    return make_user("admin@example.com", UserType.ADMIN)


@pytest.fixture
def authenticate(client):
    def _authenticate(user):
        token = AccessToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    return _authenticate


@pytest.fixture
def make_survey(provider):
    def _make_survey(
        title="Campus survey",
        status=SurveyStatus.PUBLISHED,
        region=None,
        gender=None,
        age_min=None,
        age_max=None,
    ):
        survey = Survey.objects.create(
            provider=provider,
            title=title,
            description="About campus life",
            status=status,
        )
        TargetingCriteria.objects.create(
            survey=survey,
            region=region,
            gender=gender,
            age_min=age_min,
            age_max=age_max,
        )
        return survey

    return _make_survey


@pytest.fixture
def survey(make_survey):
    """Published open survey: required choice, required rating, optional text."""
    survey = make_survey()
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="B", order_index=1)
    Question.objects.create(
        survey=survey,
        question_text="Rate us",
        question_type=QuestionType.RATING_SCALE,
        is_required=True,
        order_index=1,
    )
    Question.objects.create(
        survey=survey,
        question_text="Comments",
        question_type=QuestionType.OPEN_TEXT,
        is_required=False,
        order_index=2,
    )
    return survey
