"""Targeting page keeps one governorate select over the regions list (TASK-33)."""

import pytest
from django.urls import reverse

from apps.core.models import Survey, TargetingCriteria, User
from core.enums import AccountStatus, Gender, UserType


@pytest.fixture
def provider_client(client):
    provider = User.objects.create_user(
        email="provider-targeting-page@example.com",
        password="strong-password",
        name="Provider",
        user_type=UserType.SERVICE_PROVIDER,
        account_status=AccountStatus.ACTIVE,
    )
    client.force_login(provider)
    survey = Survey.objects.create(provider=provider, title="Draft", description="D")
    return client, survey


@pytest.mark.django_db
@pytest.mark.parametrize(("posted", "stored"), [("HOMS", ["HOMS"]), ("", [])])
def test_posting_one_governorate_stores_a_regions_list(provider_client, posted, stored):
    client, survey = provider_client

    response = client.post(
        reverse("surveys:targeting_criteria", args=[survey.survey_id]),
        {"gender": Gender.FEMALE, "age_min": "18", "age_max": "40", "region": posted},
    )

    assert response.status_code == 302
    criteria = TargetingCriteria.objects.get(survey=survey)
    assert (criteria.gender, criteria.age_min, criteria.age_max) == (Gender.FEMALE, 18, 40)
    assert criteria.regions == stored


@pytest.mark.django_db
def test_page_fills_the_select_with_the_first_stored_governorate(provider_client):
    client, survey = provider_client
    TargetingCriteria.objects.create(survey=survey, regions=["LATAKIA", "HOMS"])

    response = client.get(reverse("surveys:targeting_criteria", args=[survey.survey_id]))

    assert response.status_code == 200
    assert response.context["form"].initial["region"] == "LATAKIA"
