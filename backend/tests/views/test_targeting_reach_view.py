"""POST /surveys/<id>/targeting/reach/ returns the banded reach as JSON (TASK-34)."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.core.models import RespondentProfile, Survey, TargetingCriteria, User
from core.enums import AccountStatus, Gender, SurveyStatus, UserType


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
            user=create_user(f"respondent-reach-view-{index}@example.com", UserType.RESPONDENT),
            age=30,
            gender=Gender.FEMALE,
            region=region,
            interests=["TECHNOLOGY"],
        )


def reach_url(survey_id):
    return reverse("surveys:targeting_reach", args=[survey_id])


@pytest.fixture
def owner():
    return create_user("provider-reach-view@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(owner):
    return Survey.objects.create(provider=owner, title="Draft", description="D")


@pytest.mark.django_db
def test_owner_gets_the_four_reach_keys(client, owner, survey):
    create_respondents(["HOMS"] * 6)
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id), {"gender": ""})

    assert response.status_code == 200
    assert response.json() == {"state": "everyone", "count": 6, "total": 6, "percent": 100}
    assert not TargetingCriteria.objects.exists()


@pytest.mark.django_db
def test_repeated_list_keys_are_read(client, owner, survey):
    create_respondents(["HOMS"] * 3 + ["LATAKIA"] * 3 + ["DAMASCUS"] * 3)
    client.force_login(owner)

    response = client.post(
        reach_url(survey.survey_id),
        {"gender": Gender.FEMALE, "age_min": "18", "regions": ["HOMS", "LATAKIA"]},
    )

    assert response.status_code == 200
    assert response.json() == {"state": "narrowed", "count": 6, "total": 9, "percent": 67}


@pytest.mark.django_db
@pytest.mark.parametrize("matching", [1, 2, 3, 4])
def test_one_to_four_people_are_never_a_number(client, owner, survey, matching):
    create_respondents(["HOMS"] * matching + ["DAMASCUS"] * 6)
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id), {"regions": ["HOMS"]})

    assert response.status_code == 200
    assert response.json() == {"state": "few", "count": None, "total": 6 + matching, "percent": None}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"age_min": "50", "age_max": "20"}, "Minimum age must be less than or equal"),
        ({"regions": ["ATLANTIS"]}, "regions: "),
        ({"education_levels": ["PREFER_NOT_TO_SAY"]}, "education_levels: "),
        ({"age_min": "abc"}, "age_min: "),
    ],
)
def test_invalid_criteria_give_400(client, owner, survey, data, message):
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id), data)

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert response.json()["message"].startswith(message)


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["age_min", "age_max"])
def test_an_age_above_the_limit_is_a_field_error(client, owner, survey, field):
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id), {field: "121"})

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert response.json()["message"].startswith(f"{field}: ")


@pytest.mark.django_db
def test_without_a_session_gives_401_json(client, survey):
    response = client.post(reach_url(survey.survey_id), {})

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", [UserType.SERVICE_PROVIDER, UserType.RESPONDENT])
def test_another_provider_or_a_respondent_gets_403(client, survey, user_type):
    client.force_login(create_user("someone-else@example.com", user_type))

    response = client.post(reach_url(survey.survey_id), {})

    assert response.status_code == 403
    assert response.json()["error"] == "unauthorized_action"


@pytest.mark.django_db
def test_missing_survey_gives_404(client, owner, survey):
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id + 1000), {})

    assert response.status_code == 404
    assert response.json()["error"] == "survey_not_found"


@pytest.mark.django_db
def test_published_survey_gives_409(client, owner, survey):
    survey.status = SurveyStatus.PUBLISHED
    survey.save()
    client.force_login(owner)

    response = client.post(reach_url(survey.survey_id), {})

    assert response.status_code == 409
    assert response.json()["error"] == "not_editable"


@pytest.mark.django_db
def test_post_without_csrf_token_is_refused(owner, survey):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(owner)

    response = csrf_client.post(reach_url(survey.survey_id), {})

    assert response.status_code == 403
