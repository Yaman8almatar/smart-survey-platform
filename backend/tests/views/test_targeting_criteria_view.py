"""W-03 targeting page: chips for five lists, the server's first reach and saving (TASK-35)."""

import re

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.core.models import RespondentProfile, Survey, TargetingCriteria, User
from core.enums import AccountStatus, Gender, SurveyStatus, UserType

REACH_COPY = [
    "respondents. No restriction yet: everyone with a complete profile matches.",
    "respondents match these criteria now.",
    "Fewer than 5",
    "The exact number is hidden to protect privacy.",
    "No respondent",
    "matches these criteria yet.",
    "Could not count",
    "respondents. Your criteria are not affected.",
    "Try again",
    "No count yet",
    "Fix the highlighted field to see the reach.",
    "You can still publish. People who match later will see the survey.",
]


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
            user=create_user(f"respondent-targeting-page-{index}@example.com", UserType.RESPONDENT),
            age=30,
            gender=Gender.FEMALE,
            region=region,
            interests=["TECHNOLOGY"],
        )


def page_url(survey):
    return reverse("surveys:targeting_criteria", args=[survey.survey_id])


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def is_checked(html, name, value):
    return re.search(rf'name="{name}" value="{value}"[^>]*\bchecked\b', html) is not None


@pytest.fixture
def owner():
    return create_user("provider-targeting-page@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(owner):
    return Survey.objects.create(provider=owner, title="Draft", description="D")


@pytest.fixture
def owner_client(client, owner):
    client.force_login(owner)
    return client


@pytest.mark.django_db
def test_page_renders_saved_lists_as_checked_chips(owner_client, survey):
    TargetingCriteria.objects.create(
        survey=survey,
        gender="",
        regions=["LATAKIA", "HOMS"],
        education_levels=["BACHELOR"],
        occupations=["STUDENT"],
        marital_statuses=["SINGLE"],
        interests=["TECHNOLOGY", "EDUCATION"],
    )

    response = owner_client.get(page_url(survey))

    assert response.status_code == 200
    html = response.content.decode()
    for name, value in [
        ("regions", "LATAKIA"),
        ("regions", "HOMS"),
        ("education_levels", "BACHELOR"),
        ("occupations", "STUDENT"),
        ("marital_statuses", "SINGLE"),
        ("interests", "TECHNOLOGY"),
        ("interests", "EDUCATION"),
        ("gender", "ANY"),
    ]:
        assert is_checked(html, name, value), (name, value)
    assert not is_checked(html, "regions", "DAMASCUS")
    assert not is_checked(html, "gender", "FEMALE")
    assert "PREFER_NOT_TO_SAY" not in html
    assert f'data-reach-url="{reverse("surveys:targeting_reach", args=[survey.survey_id])}"' in html
    for copy in REACH_COPY:
        assert copy in html, copy


@pytest.mark.django_db
def test_chip_and_segment_inputs_are_not_form_controls(owner_client, survey):
    html = owner_client.get(page_url(survey)).content.decode()

    for name in ["gender", "regions", "education_levels", "occupations", "marital_statuses", "interests"]:
        inputs = re.findall(rf'<input[^>]*name="{name}"[^>]*>', html)
        assert inputs, name
        assert all("form-control" not in tag for tag in inputs), name
    assert re.search(r'<input[^>]*name="age_min"[^>]*class="form-control"', html)


@pytest.mark.django_db
def test_page_without_criteria_shows_everyone_with_any_gender(owner_client, survey):
    create_respondents(["HOMS"] * 3)

    html = owner_client.get(page_url(survey)).content.decode()

    assert 'data-state="everyone"' in html
    assert is_checked(html, "gender", "ANY")
    assert re.search(r"<span data-reach-count>3</span> of <span data-reach-total>3</span>", html)


@pytest.mark.django_db
def test_narrowed_reach_is_in_the_page(owner_client, survey):
    create_respondents(["HOMS"] * 6 + ["DAMASCUS"] * 3)
    TargetingCriteria.objects.create(survey=survey, regions=["HOMS"])

    response = owner_client.get(page_url(survey))

    html = response.content.decode()
    assert response.context["reach"]["state"] == "narrowed"
    assert 'data-state="narrowed"' in html
    assert "<span data-reach-count>6</span> of <span data-reach-total>9</span>" in html
    assert ">67%</text>" in html


@pytest.mark.django_db
def test_two_matching_respondents_are_never_shown_as_a_number(owner_client, survey):
    create_respondents(["HOMS"] * 2 + ["DAMASCUS"] * 6)
    TargetingCriteria.objects.create(survey=survey, regions=["HOMS"])

    html = owner_client.get(page_url(survey)).content.decode()

    assert 'data-state="few"' in html
    assert ">&lt;5</text>" in html
    assert "<span data-reach-count></span> of <span data-reach-total></span>" in html
    assert not re.search(r">\s*2\s*</span>\s*of", html)
    assert "2 of" not in html


@pytest.mark.django_db
def test_post_saves_gender_ages_and_all_five_lists(owner_client, survey):
    response = owner_client.post(
        page_url(survey),
        {
            "gender": Gender.FEMALE,
            "age_min": "18",
            "age_max": "34",
            "regions": ["HOMS", "HAMA"],
            "education_levels": ["BACHELOR", "MASTER"],
            "occupations": ["STUDENT"],
            "marital_statuses": ["SINGLE"],
            "interests": ["TECHNOLOGY", "EDUCATION"],
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["Targeting criteria saved successfully."]
    criteria = TargetingCriteria.objects.get(survey=survey)
    assert (criteria.gender, criteria.age_min, criteria.age_max) == (Gender.FEMALE, 18, 34)
    assert criteria.regions == ["HOMS", "HAMA"]
    assert criteria.education_levels == ["BACHELOR", "MASTER"]
    assert criteria.occupations == ["STUDENT"]
    assert criteria.marital_statuses == ["SINGLE"]
    assert criteria.interests == ["TECHNOLOGY", "EDUCATION"]


@pytest.mark.django_db
def test_post_with_min_above_max_saves_nothing_and_marks_age_min(owner_client, survey):
    response = owner_client.post(
        page_url(survey), {"gender": Gender.ANY, "age_min": "40", "age_max": "30"}
    )

    assert response.status_code == 200
    assert not TargetingCriteria.objects.exists()
    assert response.context["form"].errors == {
        "age_min": ["Minimum age must be less than or equal to maximum age."]
    }
    html = response.content.decode()
    assert 'data-state="invalid"' in html
    assert 'class="col-sm-6 age-field is-invalid" data-age-field="age_min"' in html
    assert re.search(
        r'data-age-field="age_min".*?<span data-field-error-text>'
        r"Minimum age must be less than or equal to maximum age.</span>",
        html,
        re.S,
    )


@pytest.mark.django_db
def test_post_with_an_unrealistic_age_is_a_field_error(owner_client, survey):
    response = owner_client.post(page_url(survey), {"gender": Gender.ANY, "age_max": "121"})

    assert response.status_code == 200
    assert not TargetingCriteria.objects.exists()
    assert "age_max" in response.context["form"].errors
    assert 'data-state="invalid"' in response.content.decode()


@pytest.mark.django_db
def test_published_survey_redirects_with_the_service_message(owner_client, survey):
    survey.status = SurveyStatus.PUBLISHED
    survey.save()

    response = owner_client.get(page_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["Targeting criteria can only be updated for draft surveys."]


@pytest.mark.django_db
def test_another_provider_is_redirected(client, survey):
    client.force_login(create_user("other-provider@example.com", UserType.SERVICE_PROVIDER))

    response = client.get(page_url(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:survey_list")
    assert messages_of(response) == ["Survey not found."]
