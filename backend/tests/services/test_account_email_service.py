import re
from datetime import datetime, timedelta

import pytest
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import User
from core.enums import AccountStatus, Gender, UserType
from core.exceptions import EmailNotConfirmed, InvalidCredentials, ValidationError
from repositories.user_repository import UserRepository
from services import account_email_service as module
from services.account_email_service import AccountEmailService, email_confirmation_token
from services.authentication_service import AuthenticationService

BASE_URL = "http://testserver/"
PASSWORD = "strong-password"
NEW_PASSWORD = "a-new-strong-pass-7"
CONFIRM_INVALID = "This link is not valid or has expired. Send a new one."
RESET_INVALID = "This link is not valid or has expired. Ask for a new one."
NOT_CONFIRMED = "Confirm your email address first. Open the link we sent you, or send a new one."

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    """Start every test with no 300-second slot taken."""
    cache.clear()


@pytest.fixture
def service():
    return AccountEmailService()


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
        user_type=UserType.RESPONDENT,
    )


def uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def link_parts(message):
    """Return (uidb64, token) from the only link in an email body."""
    match = re.search(r"http://testserver/users/[a-z-]+/([^/\s]+)/([^/\s]+)/", message.body)
    return match.group(1), match.group(2)


def refreshed(user):
    return User.objects.get(pk=user.pk)


# Accounts and the log-in order


def test_both_registrations_start_unconfirmed():
    auth = AuthenticationService()
    provider = auth.register_service_provider(name="P", email="p@example.com", password=PASSWORD)
    respondent = auth.register_respondent(
        name="R",
        email="r@example.com",
        password=PASSWORD,
        age=30,
        gender=Gender.MALE,
        region="DAMASCUS",
        interests=["SPORTS"],
    )

    assert refreshed(provider).email_verified is False
    assert refreshed(respondent).email_verified is False


def test_accounts_made_by_create_user_stay_confirmed(confirmed):
    assert refreshed(confirmed).email_verified is True


def test_unconfirmed_account_with_right_password_gets_email_not_confirmed(unconfirmed):
    with pytest.raises(EmailNotConfirmed) as error:
        AuthenticationService().authenticate_user("lina@example.com", PASSWORD)

    assert str(error.value) == NOT_CONFIRMED


def test_wrong_password_is_checked_before_confirmation(unconfirmed):
    with pytest.raises(InvalidCredentials, match="Invalid email or password."):
        AuthenticationService().authenticate_user("lina@example.com", "bad-password")


@pytest.mark.parametrize("status", [AccountStatus.SUSPENDED, AccountStatus.DELETED])
def test_suspended_or_deleted_is_checked_before_confirmation(unconfirmed, status):
    unconfirmed.account_status = status
    UserRepository().update(unconfirmed)

    with pytest.raises(InvalidCredentials, match="Account is suspended or deleted."):
        AuthenticationService().authenticate_user("lina@example.com", PASSWORD)


def test_confirmed_account_logs_in(service, unconfirmed):
    service.confirm_email(uid(unconfirmed), email_confirmation_token.make_token(unconfirmed))

    user = AuthenticationService().authenticate_user("lina@example.com", PASSWORD)

    assert user.pk == unconfirmed.pk


# Confirmation


def test_send_confirmation_sends_the_approved_email(service, unconfirmed):
    service.send_confirmation(unconfirmed, BASE_URL)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "Confirm your Smart Survey email address"
    assert message.to == ["lina@example.com"]
    assert message.from_email == "Smart Survey <no-reply@smartsurvey.local>"
    uidb64, token = link_parts(message)
    link = f"http://testserver/users/confirm-email/{uidb64}/{token}/"
    assert message.body == (
        "Hello Lina,\n\n"
        "Confirm your email address for the Smart Survey Platform by opening this link:\n\n"
        f"{link}\n\n"
        "The link works for 3 days. If you did not create an account, you can ignore this email.\n\n"
        "Smart Survey Platform"
    )
    assert uidb64 == uid(unconfirmed)


def test_confirmation_link_confirms_the_account(service, unconfirmed):
    service.send_confirmation(unconfirmed, BASE_URL)

    user = service.confirm_email(*link_parts(mail.outbox[0]))

    assert user.pk == unconfirmed.pk
    assert refreshed(unconfirmed).email_verified is True


def test_used_confirmation_link_is_refused(service, unconfirmed):
    service.send_confirmation(unconfirmed, BASE_URL)
    parts = link_parts(mail.outbox[0])
    service.confirm_email(*parts)

    with pytest.raises(ValidationError) as error:
        service.confirm_email(*parts)

    assert str(error.value) == CONFIRM_INVALID


@pytest.mark.parametrize(
    "uidb64, token",
    [("bm90LWFuLWlk", "abc-123"), ("!!!", "abc-123"), ("OTk5OTk5", "abc-123")],
)
def test_wrong_confirmation_link_is_refused(service, unconfirmed, uidb64, token):
    with pytest.raises(ValidationError, match=re.escape(CONFIRM_INVALID)):
        service.confirm_email(uidb64, token)

    assert refreshed(unconfirmed).email_verified is False


def test_confirmation_token_of_another_account_is_refused(service, unconfirmed):
    other = AuthenticationService().register_service_provider(
        name="Other", email="other@example.com", password=PASSWORD
    )

    with pytest.raises(ValidationError, match=re.escape(CONFIRM_INVALID)):
        service.confirm_email(uid(unconfirmed), email_confirmation_token.make_token(other))


def test_reset_token_does_not_confirm_an_email(service, unconfirmed):
    with pytest.raises(ValidationError, match=re.escape(CONFIRM_INVALID)):
        service.confirm_email(uid(unconfirmed), default_token_generator.make_token(unconfirmed))


def test_expired_confirmation_link_is_refused(service, unconfirmed, monkeypatch):
    token = email_confirmation_token.make_token(unconfirmed)
    monkeypatch.setattr(
        email_confirmation_token, "_now", lambda: datetime.now() + timedelta(days=3, hours=1)
    )

    with pytest.raises(ValidationError, match=re.escape(CONFIRM_INVALID)):
        service.confirm_email(uid(unconfirmed), token)


def test_resend_sends_one_link_to_an_unconfirmed_account(service, unconfirmed):
    service.resend_confirmation("  LINA@Example.com ", BASE_URL)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Confirm your Smart Survey email address"


def test_resend_sends_at_most_once_in_300_seconds(service, unconfirmed):
    service.resend_confirmation("lina@example.com", BASE_URL)
    service.resend_confirmation("LINA@example.com", BASE_URL)

    assert len(mail.outbox) == 1


def test_resend_sends_again_once_the_300_seconds_have_passed(service, unconfirmed):
    service.resend_confirmation("lina@example.com", BASE_URL)
    cache.delete("account_email:confirmation:lina@example.com")  # the slot expired
    service.resend_confirmation("lina@example.com", BASE_URL)

    assert len(mail.outbox) == 2


def test_the_slot_is_a_300_second_cache_add_on_the_lower_cased_address(
    service, unconfirmed, monkeypatch
):
    calls = []

    class RecordingCache:
        def add(self, key, value, timeout):
            calls.append((key, timeout))
            return True

    monkeypatch.setattr(module, "cache", RecordingCache())
    service.resend_confirmation("Lina@Example.COM", BASE_URL)
    service.send_password_reset("Lina@Example.COM", BASE_URL)

    assert calls == [
        ("account_email:confirmation:lina@example.com", 300),
        ("account_email:password_reset:lina@example.com", 300),
    ]


def test_resend_sends_nothing_to_a_confirmed_account(service, confirmed):
    service.resend_confirmation("omar@example.com", BASE_URL)

    assert mail.outbox == []


def test_resend_sends_nothing_to_a_suspended_account(service, unconfirmed):
    unconfirmed.suspend()
    UserRepository().update(unconfirmed)

    service.resend_confirmation("lina@example.com", BASE_URL)

    assert mail.outbox == []


def test_resend_to_an_unknown_address_sends_nothing_and_does_not_raise(service):
    service.resend_confirmation("nobody@example.com", BASE_URL)

    assert mail.outbox == []


# Password reset


def test_send_password_reset_sends_the_approved_email(service, confirmed):
    service.send_password_reset("omar@example.com", BASE_URL)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "Reset your Smart Survey password"
    assert message.to == ["omar@example.com"]
    assert message.from_email == "Smart Survey <no-reply@smartsurvey.local>"
    uidb64, token = link_parts(message)
    link = f"http://testserver/users/password-reset/{uidb64}/{token}/"
    assert message.body == (
        "Hello Omar,\n\n"
        "To choose a new password for the Smart Survey Platform, open this link:\n\n"
        f"{link}\n\n"
        "The link works for 3 days and only once. If you did not ask for a new password, "
        "you can ignore this email; your password stays the same.\n\n"
        "Smart Survey Platform"
    )


def test_password_reset_sends_at_most_once_in_300_seconds(service, confirmed):
    service.send_password_reset("omar@example.com", BASE_URL)
    service.send_password_reset("OMAR@example.com", BASE_URL)

    assert len(mail.outbox) == 1


def test_password_reset_and_resend_have_separate_slots(service, unconfirmed):
    service.resend_confirmation("lina@example.com", BASE_URL)
    service.send_password_reset("lina@example.com", BASE_URL)

    assert [m.subject for m in mail.outbox] == [
        "Confirm your Smart Survey email address",
        "Reset your Smart Survey password",
    ]


def test_password_reset_to_an_unknown_address_sends_nothing_and_does_not_raise(service):
    service.send_password_reset("nobody@example.com", BASE_URL)

    assert mail.outbox == []


def test_password_reset_sends_nothing_to_a_suspended_account(service, confirmed):
    confirmed.suspend()
    UserRepository().update(confirmed)

    service.send_password_reset("omar@example.com", BASE_URL)

    assert mail.outbox == []


def test_password_reset_sends_nothing_without_a_usable_password(service, confirmed):
    confirmed.set_unusable_password()
    UserRepository().update(confirmed)

    service.send_password_reset("omar@example.com", BASE_URL)

    assert mail.outbox == []


def test_reset_sets_the_password_and_confirms_the_email(service, unconfirmed):
    service.send_password_reset("lina@example.com", BASE_URL)

    service.reset_password(*link_parts(mail.outbox[0]), NEW_PASSWORD, NEW_PASSWORD)

    user = refreshed(unconfirmed)
    assert user.check_password(NEW_PASSWORD)
    assert user.email_verified is True
    assert AuthenticationService().authenticate_user("lina@example.com", NEW_PASSWORD)


def test_reset_link_works_only_once(service, confirmed):
    service.send_password_reset("omar@example.com", BASE_URL)
    parts = link_parts(mail.outbox[0])
    service.reset_password(*parts, NEW_PASSWORD, NEW_PASSWORD)

    with pytest.raises(ValidationError) as error:
        service.reset_password(*parts, "another-strong-pass-9", "another-strong-pass-9")

    assert str(error.value) == RESET_INVALID
    assert refreshed(confirmed).check_password(NEW_PASSWORD)


def test_wrong_reset_link_is_refused(service, confirmed):
    with pytest.raises(ValidationError, match=re.escape(RESET_INVALID)):
        service.reset_password(uid(confirmed), "abc-123", NEW_PASSWORD, NEW_PASSWORD)

    assert refreshed(confirmed).check_password(PASSWORD)


def test_confirmation_token_does_not_reset_a_password(service, confirmed):
    token = email_confirmation_token.make_token(confirmed)

    with pytest.raises(ValidationError, match=re.escape(RESET_INVALID)):
        service.reset_password(uid(confirmed), token, NEW_PASSWORD, NEW_PASSWORD)


def test_check_password_reset_link(service, confirmed):
    token = default_token_generator.make_token(confirmed)

    assert service.check_password_reset_link(uid(confirmed), token).pk == confirmed.pk
    with pytest.raises(ValidationError, match=re.escape(RESET_INVALID)):
        service.check_password_reset_link("!!!", token)


def test_reset_refuses_different_passwords_with_djangos_message(service, confirmed):
    token = default_token_generator.make_token(confirmed)

    with pytest.raises(ValidationError) as error:
        service.reset_password(uid(confirmed), token, NEW_PASSWORD, "another-strong-pass-9")

    assert str(error.value) == SetPasswordForm.error_messages["password_mismatch"]
    assert refreshed(confirmed).check_password(PASSWORD)


def test_reset_refuses_a_weak_password_with_djangos_message(service, confirmed):
    token = default_token_generator.make_token(confirmed)

    with pytest.raises(ValidationError) as error:
        service.reset_password(uid(confirmed), token, "123", "123")

    assert "This password is too short." in str(error.value)
    assert refreshed(confirmed).check_password(PASSWORD)


def test_reset_ends_every_app_session_of_the_account(service, confirmed):
    first = RefreshToken.for_user(confirmed)
    second = RefreshToken.for_user(confirmed)
    other_user = User.objects.create_user(
        email="other@example.com", password=PASSWORD, name="Other", user_type=UserType.RESPONDENT
    )
    other = RefreshToken.for_user(other_user)
    token = default_token_generator.make_token(confirmed)

    service.reset_password(uid(confirmed), token, NEW_PASSWORD, NEW_PASSWORD)

    assert BlacklistedToken.objects.filter(token__user=confirmed).count() == 2
    for refresh in (first, second):
        with pytest.raises(TokenError):
            RefreshToken(str(refresh))
    assert RefreshToken(str(other))["user_id"] == str(other_user.pk)


def test_reset_rolls_back_when_ending_the_sessions_fails(service, confirmed, monkeypatch):
    token = default_token_generator.make_token(confirmed)

    def fail(user):
        raise RuntimeError("blacklist failed")

    monkeypatch.setattr(service.user_repository, "blacklist_refresh_tokens", fail)

    with pytest.raises(RuntimeError):
        service.reset_password(uid(confirmed), token, NEW_PASSWORD, NEW_PASSWORD)

    assert refreshed(confirmed).check_password(PASSWORD)
