"""FR-16: the order settings on the create and edit survey forms (TASK-52)."""

import re

import pytest
from django.urls import reverse

from apps.core.models import Survey, User
from core.enums import AccountStatus, UserType

pytestmark = pytest.mark.django_db

COPY = [
    "Order for respondents",
    "Shuffle the order of questions",
    "Each respondent sees the questions in an order of their own, "
    "which stays the same if they leave and come back.",
    "Shuffle the order of answer options",
    "Applies to multiple-choice questions. Rating scales keep their order.",
]


@pytest.fixture
def owner():
    return User.objects.create_user(
        email="provider-shuffle-view@example.com",
        password="strong-password",
        name="Provider",
        user_type=UserType.SERVICE_PROVIDER,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def owner_client(client, owner):
    client.force_login(owner)
    return client


def edit_url(survey):
    return reverse("surveys:edit_survey", args=[survey.survey_id])


def checkbox(html, name):
    """Return the <input> tag of the named checkbox."""
    return re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)


@pytest.mark.parametrize("page", ["create", "edit"])
def test_both_forms_show_the_heading_labels_and_help_lines(owner_client, owner, page):
    if page == "create":
        url = reverse("surveys:create_survey")
    else:
        url = edit_url(Survey.objects.create(provider=owner, title="T", description="D"))

    html = owner_client.get(url).content.decode()

    for text in COPY:
        assert text in html
    assert 'type="checkbox"' in checkbox(html, "shuffle_questions")
    assert 'class="form-check-input"' in checkbox(html, "shuffle_options")


def test_posting_the_create_form_stores_the_settings(owner_client):
    owner_client.post(
        reverse("surveys:create_survey"),
        {"title": "New", "description": "", "shuffle_questions": "on"},
    )

    survey = Survey.objects.get(title="New")
    assert (survey.shuffle_questions, survey.shuffle_options) == (True, False)


def test_posting_the_edit_form_stores_the_settings(owner_client, owner):
    survey = Survey.objects.create(
        provider=owner, title="T", description="D", shuffle_questions=True
    )

    owner_client.post(
        edit_url(survey), {"title": "T", "description": "D", "shuffle_options": "on"}
    )
    survey.refresh_from_db()

    assert (survey.shuffle_questions, survey.shuffle_options) == (False, True)


def test_the_edit_form_shows_the_stored_values_checked(owner_client, owner):
    survey = Survey.objects.create(
        provider=owner, title="T", description="D", shuffle_options=True
    )

    html = owner_client.get(edit_url(survey)).content.decode()

    assert "checked" in checkbox(html, "shuffle_options")
    assert "checked" not in checkbox(html, "shuffle_questions")
