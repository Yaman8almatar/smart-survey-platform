"""Publish goes through a confirmation page with the reach and the targeting (TASK-35, P-19)."""

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.core.models import Question, RespondentProfile, Survey, TargetingCriteria, User
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_respondents(regions):
    for index, region in enumerate(regions):
        RespondentProfile.objects.create(
            user=create_user(f"respondent-publish-{index}@example.com", UserType.RESPONDENT),
            age=25,
            gender=Gender.FEMALE,
            region=region,
            interests=["TECHNOLOGY"],
        )


def add_questions(survey, count):
    for index in range(count):
        Question.objects.create(
            survey=survey,
            question_text=f"Question {index}",
            question_type=QuestionType.OPEN_TEXT,
            is_required=True,
            order_index=index,
        )


def publish_url(survey):
    return reverse("surveys:submit_for_review", args=[survey.survey_id])


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


@pytest.fixture
def owner():
    return create_user("provider-publish@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(owner):
    return Survey.objects.create(provider=owner, title="Public transport", description="D")


@pytest.fixture
def owner_client(client, owner):
    client.force_login(owner)
    return client


@pytest.mark.django_db
def test_confirmation_shows_reach_criteria_rows_and_question_count(owner_client, survey):
    create_respondents(["HOMS"] * 6 + ["DAMASCUS"] * 3)
    add_questions(survey, 2)
    TargetingCriteria.objects.create(
        survey=survey,
        gender=Gender.FEMALE,
        age_min=18,
        age_max=34,
        regions=["HOMS", "HAMA"],
        interests=["TECHNOLOGY", "EDUCATION"],
    )

    response = owner_client.get(publish_url(survey))

    assert response.status_code == 200
    html = response.content.decode()
    assert "6 of 9 respondents" in html
    assert "match the targeting now and will see the survey once it is published." in html
    assert "<dt>Gender</dt><dd>Female</dd>" in html
    assert "<dt>Age</dt><dd>18 to 34</dd>" in html
    assert "<dt>Governorates</dt><dd>Homs, Hama</dd>" in html
    assert "<dt>Education level</dt><dd>Any</dd>" in html
    assert "<dt>Occupation</dt><dd>Any</dd>" in html
    assert "<dt>Marital status</dt><dd>Any</dd>" in html
    assert "<dt>Interests</dt><dd>At least one of: Technology, Education</dd>" in html
    assert "2 questions" in html
    assert "Submit for review" in html
    assert "Check who will see the survey before you submit it for review." in html
    assert (
        "After you submit it, the questions and the targeting can no longer be changed. "
        "An admin then publishes the survey or returns it to you with a reason."
    ) in html
    assert "You can still submit it. People who match later will see the survey." not in html
    assert reverse("surveys:targeting_criteria", args=[survey.survey_id]) in html
    assert 'method="post"' in html
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.DRAFT


@pytest.mark.django_db
def test_open_criteria_and_one_question(owner_client, survey):
    create_respondents(["HOMS"] * 5)
    add_questions(survey, 1)
    TargetingCriteria.objects.create(survey=survey, gender=Gender.ANY)

    html = owner_client.get(publish_url(survey)).content.decode()

    assert "5 of 5 respondents" in html
    assert "<dt>Gender</dt><dd>Any</dd>" in html
    assert "<dt>Age</dt><dd>Any</dd>" in html
    assert "<dt>Interests</dt><dd>Any</dd>" in html
    assert "1 question<" in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("matching", "big_line", "warning"),
    [
        (2, "Fewer than 5 respondents", "Fewer than 5 respondents match now."),
        (0, "No respondent", "No respondent matches these criteria yet."),
    ],
)
def test_few_and_none_show_their_warning(owner_client, survey, matching, big_line, warning):
    create_respondents(["HOMS"] * matching + ["DAMASCUS"] * 6)
    add_questions(survey, 1)
    TargetingCriteria.objects.create(survey=survey, regions=["HOMS"])

    html = owner_client.get(publish_url(survey)).content.decode()

    assert big_line in html
    ring_centre = ">&lt;5</text>" if matching else ">0</text>"
    assert ring_centre in html
    assert warning in html
    assert "You can still submit it. People who match later will see the survey." in html
    assert f"{matching} of" not in html


@pytest.mark.django_db
def test_survey_without_questions_redirects_with_the_service_message(owner_client, survey):
    TargetingCriteria.objects.create(survey=survey)

    response = owner_client.get(publish_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["A survey must have at least one question."]


@pytest.mark.django_db
def test_survey_without_criteria_redirects_with_the_service_message(owner_client, survey):
    add_questions(survey, 1)

    response = owner_client.get(publish_url(survey))

    assert response.status_code == 302
    assert messages_of(response) == ["Survey targeting criteria is required."]


@pytest.mark.django_db
def test_another_providers_survey_redirects_with_the_service_message(client, survey):
    add_questions(survey, 1)
    TargetingCriteria.objects.create(survey=survey)
    client.force_login(create_user("other-provider@example.com", UserType.SERVICE_PROVIDER))

    response = client.get(publish_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["Only the survey owner can perform this action."]


@pytest.mark.django_db
def test_post_submits_for_review_and_stores_no_reach_yet(owner_client, survey):
    create_respondents(["HOMS"] * 6 + ["DAMASCUS"] * 3)
    add_questions(survey, 1)
    TargetingCriteria.objects.create(survey=survey, regions=["HOMS"])

    response = owner_client.post(publish_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["Survey submitted for review."]
    survey.refresh_from_db()
    assert survey.status == SurveyStatus.PENDING_REVIEW
    assert survey.reach_at_publish is None


@pytest.mark.django_db
def test_survey_list_renders_publish_as_a_link(owner_client, survey):
    add_questions(survey, 1)
    TargetingCriteria.objects.create(survey=survey)

    html = owner_client.get(reverse("surveys:survey_list")).content.decode()

    assert f'href="{publish_url(survey)}"' in html
    assert f'action="{publish_url(survey)}"' not in html
