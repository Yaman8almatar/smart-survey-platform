"""P-09 (TASK-41): the respondent web pages are gone; one page sends respondents to the app."""

import pytest
from django.urls import reverse

from apps.core.models import RespondentProfile, User
from core.enums import AccountStatus, Gender, UserType

pytestmark = pytest.mark.django_db

PASSWORD = "strong-password"
OLD_PATHS = [
    "/responses/respondent/dashboard/",
    "/responses/profile/",
    "/responses/eligible-surveys/",
    "/responses/answered-surveys/",
    "/responses/surveys/1/submit/",
    "/responses/submission-confirmation/",
]


def make_user(email, user_type):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )
    if user_type == UserType.RESPONDENT:
        RespondentProfile.objects.create(
            user=user, age=30, gender=Gender.MALE, region="DAMASCUS", interests=["SPORTS"]
        )
    return user


@pytest.mark.parametrize("path", OLD_PATHS)
def test_old_respondent_pages_give_404(client, path):
    client.force_login(make_user("respondent-old@example.com", UserType.RESPONDENT))

    assert client.get(path).status_code == 404


def test_respondent_who_signs_in_lands_on_the_app_page(client):
    make_user("respondent-login@example.com", UserType.RESPONDENT)

    response = client.post(
        reverse("users:login"),
        {"email": "respondent-login@example.com", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == "/respondent/"
    page = client.get(response.url)
    content = page.content.decode()
    assert page.status_code == 200
    assert "Answer surveys in the app" in content
    assert "Sign in there with this email and password." in content
    assert reverse("users:logout") in content


@pytest.mark.parametrize(
    "user_type, dashboard",
    [
        (UserType.SERVICE_PROVIDER, "surveys:provider_dashboard"),
        (UserType.ADMIN, "admin_panel:admin_dashboard"),
    ],
)
def test_other_roles_are_sent_to_their_own_dashboard(client, user_type, dashboard):
    client.force_login(make_user(f"{user_type.lower()}-app@example.com", user_type))

    response = client.get(reverse("responses:use_app"))

    assert response.status_code == 302
    assert response.url == reverse(dashboard)


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get(reverse("responses:use_app"))

    assert response.status_code == 302
    assert response.url == reverse("users:login")


def test_home_page_shows_respondents_only_the_app_card(client):
    client.force_login(make_user("respondent-home@example.com", UserType.RESPONDENT))

    content = client.get(reverse("home")).content.decode()

    assert 'href="/respondent/"' in content
    assert "/responses/" not in content
