import re

import pytest
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.models import User
from core.enums import UserType
from services.account_email_service import email_confirmation_token
from services.authentication_service import AuthenticationService

PASSWORD = "strong-password"
NEW_PASSWORD = "a-new-strong-pass-7"
NOT_CONFIRMED = "Confirm your email address first. Open the link we sent you, or send a new one."
RESEND_DONE = "If an unconfirmed account uses this email, we sent a new link. Check your inbox."
RESET_DONE = "If an account uses this email, we sent a link to reset its password. Check your inbox."

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    """Start every test with no 300-second slot taken."""
    cache.clear()


@pytest.fixture
def unconfirmed():
    return AuthenticationService().register_service_provider(
        name="Lina", email="lina@example.com", password=PASSWORD
    )


@pytest.fixture
def confirmed():
    return User.objects.create_user(
        email="omar@example.com",
        password=PASSWORD,
        name="Omar",
        user_type=UserType.SERVICE_PROVIDER,
    )


def uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def confirm_url(user):
    return reverse("users:confirm_email", args=[uid(user), email_confirmation_token.make_token(user)])


def reset_url(user):
    return reverse(
        "users:password_reset_confirm", args=[uid(user), default_token_generator.make_token(user)]
    )


def refreshed(user):
    return User.objects.get(pk=user.pk)


# Registration


def test_provider_registration_sends_the_link_and_redirects_to_log_in(client):
    response = client.post(
        reverse("users:register_service_provider"),
        {
            "name": "Lina",
            "email": "Lina@Example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == [
        "Account created. We sent a confirmation link to lina@example.com. Open it, then log in."
    ]
    assert len(mail.outbox) == 1
    assert "http://testserver/users/confirm-email/" in mail.outbox[0].body


def test_respondent_registration_sends_the_link_and_redirects_to_log_in(client):
    response = client.post(
        reverse("users:register_respondent"),
        {
            "name": "Sara",
            "email": "sara@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "age": 28,
            "gender": "FEMALE",
            "region": "ALEPPO",
            "interests": ["EDUCATION"],
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == [
        "Account created. We sent a confirmation link to sara@example.com. Open it, then log in."
    ]
    assert len(mail.outbox) == 1
    assert refreshed(User.objects.get(email="sara@example.com")).email_verified is False


# Log-in page


def test_log_in_page_links_to_the_reset_page(client):
    content = client.get(reverse("users:login")).content.decode()

    assert f'<a href="{reverse("users:password_reset")}">Forgot your password?</a>' in content
    assert "Send the link again" not in content


def test_unconfirmed_log_in_shows_the_message_and_the_resend_link(client, unconfirmed):
    response = client.post(
        reverse("users:login"), {"email": "lina@example.com", "password": PASSWORD}
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert NOT_CONFIRMED in content
    assert (
        f'<a href="{reverse("users:resend_confirmation")}">Send the link again</a>' in content
    )
    assert content.index(NOT_CONFIRMED) < content.index("Send the link again")
    assert "_auth_user_id" not in client.session


def test_wrong_password_on_an_unconfirmed_account_shows_no_resend_link(client, unconfirmed):
    response = client.post(
        reverse("users:login"), {"email": "lina@example.com", "password": "bad-password"}
    )

    assert "Send the link again" not in response.content.decode()
    assert messages_of(response) == ["Invalid email or password."]


def test_confirmed_account_logs_in_on_the_website(client, unconfirmed):
    client.get(confirm_url(unconfirmed))

    response = client.post(
        reverse("users:login"), {"email": "lina@example.com", "password": PASSWORD}
    )

    assert response.status_code == 302
    assert "_auth_user_id" in client.session


# Confirmation link


def test_confirmation_link_confirms_and_redirects_to_log_in(client, unconfirmed):
    response = client.get(confirm_url(unconfirmed))

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == ["Email confirmed. You can now log in."]
    assert refreshed(unconfirmed).email_verified is True


def test_bad_confirmation_link_redirects_to_the_resend_page(client, unconfirmed):
    response = client.get(reverse("users:confirm_email", args=[uid(unconfirmed), "abc-123"]))

    assert response.status_code == 302
    assert response.url == reverse("users:resend_confirmation")
    assert messages_of(response) == ["This link is not valid or has expired. Send a new one."]
    assert refreshed(unconfirmed).email_verified is False


def test_used_confirmation_link_redirects_to_the_resend_page(client, unconfirmed):
    url = confirm_url(unconfirmed)
    client.get(url)

    response = client.get(url)

    assert response.url == reverse("users:resend_confirmation")


def test_confirmation_link_accepts_only_get(client, unconfirmed):
    response = client.post(confirm_url(unconfirmed))

    assert response.status_code == 405
    assert refreshed(unconfirmed).email_verified is False


# Resend page


def test_resend_page_shows_the_approved_copy(client):
    response = client.get(reverse("users:resend_confirmation"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Send the confirmation link again" in content
    assert "Enter the email address you registered with." in content
    assert re.search(r"<label[^>]*>\s*Email\s*</label>", content)
    assert re.search(r"</i>\s*Send link\s*</button>", content)
    assert 'method="post"' in content
    assert "csrfmiddlewaretoken" in content


def test_resend_sends_a_link_and_redirects_to_log_in(client, unconfirmed):
    response = client.post(reverse("users:resend_confirmation"), {"email": "lina@example.com"})

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == [RESEND_DONE]
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("email", ["nobody@example.com", "omar@example.com"])
def test_resend_answers_the_same_for_any_address(client, unconfirmed, confirmed, email):
    known = client.post(reverse("users:resend_confirmation"), {"email": "lina@example.com"})
    other = Client().post(reverse("users:resend_confirmation"), {"email": email})

    assert (other.status_code, other.url) == (known.status_code, known.url)
    assert messages_of(other) == messages_of(known) == [RESEND_DONE]
    assert len(mail.outbox) == 1


def test_resend_with_an_invalid_address_shows_the_form_again(client):
    response = client.post(reverse("users:resend_confirmation"), {"email": "not-an-email"})

    assert response.status_code == 200
    assert "Send the confirmation link again" in response.content.decode()
    assert mail.outbox == []


# Password reset request page


def test_reset_request_page_shows_the_approved_copy(client):
    response = client.get(reverse("users:password_reset"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Reset your password" in content
    assert (
        "Enter the email address of your account. "
        "We will send you a link to choose a new password." in content
    )
    assert re.search(r"<label[^>]*>\s*Email\s*</label>", content)
    assert re.search(r"</i>\s*Send link\s*</button>", content)
    assert "csrfmiddlewaretoken" in content


def test_reset_request_sends_a_link_and_redirects_to_log_in(client, confirmed):
    response = client.post(reverse("users:password_reset"), {"email": "omar@example.com"})

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == [RESET_DONE]
    assert len(mail.outbox) == 1
    assert "http://testserver/users/password-reset/" in mail.outbox[0].body


def test_reset_request_answers_the_same_for_an_unknown_address(client, confirmed):
    known = client.post(reverse("users:password_reset"), {"email": "omar@example.com"})
    unknown = Client().post(reverse("users:password_reset"), {"email": "nobody@example.com"})

    assert (unknown.status_code, unknown.url) == (known.status_code, known.url)
    assert messages_of(unknown) == messages_of(known) == [RESET_DONE]
    assert len(mail.outbox) == 1


# New password page


def test_new_password_page_shows_the_approved_copy(client, confirmed):
    response = client.get(reset_url(confirmed))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Choose a new password" in content
    assert re.search(r"<label[^>]*>\s*New password\s*</label>", content)
    assert re.search(r"<label[^>]*>\s*Confirm new password\s*</label>", content)
    assert re.search(r"</i>\s*Change password\s*</button>", content)
    assert "csrfmiddlewaretoken" in content


@pytest.mark.parametrize("method", ["get", "post"])
def test_bad_reset_link_shows_the_message_on_the_request_page(client, confirmed, method):
    url = reverse("users:password_reset_confirm", args=[uid(confirmed), "abc-123"])

    response = getattr(client, method)(
        url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )

    assert response.status_code == 302
    assert response.url == reverse("users:password_reset")
    assert messages_of(response) == ["This link is not valid or has expired. Ask for a new one."]
    assert refreshed(confirmed).check_password(PASSWORD)


def test_new_password_changes_it_and_redirects_to_log_in(client, confirmed):
    response = client.post(
        reset_url(confirmed), {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )

    assert response.status_code == 302
    assert response.url == reverse("users:login")
    assert messages_of(response) == ["Your password has been changed. You can now log in."]
    assert refreshed(confirmed).check_password(NEW_PASSWORD)


def test_used_reset_link_shows_the_message_on_the_request_page(client, confirmed):
    url = reset_url(confirmed)
    client.post(url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

    response = client.get(url)

    assert response.url == reverse("users:password_reset")


def test_different_new_passwords_show_djangos_message(client, confirmed):
    response = client.post(
        reset_url(confirmed),
        {"new_password1": NEW_PASSWORD, "new_password2": "another-strong-pass-9"},
    )

    assert response.status_code == 200
    assert response.context["error_message"] == SetPasswordForm.error_messages["password_mismatch"]
    assert refreshed(confirmed).check_password(PASSWORD)


def test_weak_new_password_shows_djangos_message(client, confirmed):
    response = client.post(reset_url(confirmed), {"new_password1": "123", "new_password2": "123"})

    assert response.status_code == 200
    assert "This password is too short." in response.content.decode()
    assert refreshed(confirmed).check_password(PASSWORD)


def test_reset_through_the_website_confirms_an_unconfirmed_email(client, unconfirmed):
    client.post(
        reset_url(unconfirmed), {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )

    assert refreshed(unconfirmed).email_verified is True


# Public pages, POST with CSRF


@pytest.mark.parametrize(
    "name", ["users:resend_confirmation", "users:password_reset", "users:login"]
)
def test_pages_are_public(client, name):
    assert client.get(reverse(name)).status_code == 200


def test_new_password_page_is_public(client, confirmed):
    assert client.get(reset_url(confirmed)).status_code == 200


@pytest.mark.parametrize(
    "name, data",
    [
        ("users:resend_confirmation", {"email": "lina@example.com"}),
        ("users:password_reset", {"email": "lina@example.com"}),
    ],
)
def test_request_forms_refuse_a_post_without_csrf(name, data, unconfirmed):
    response = Client(enforce_csrf_checks=True).post(reverse(name), data)

    assert response.status_code == 403
    assert mail.outbox == []


def test_new_password_form_refuses_a_post_without_csrf(confirmed):
    response = Client(enforce_csrf_checks=True).post(
        reset_url(confirmed), {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )

    assert response.status_code == 403
    assert refreshed(confirmed).check_password(PASSWORD)
