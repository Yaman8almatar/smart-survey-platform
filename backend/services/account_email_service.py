from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from core.enums import AccountStatus
from core.exceptions import ValidationError
from repositories.user_repository import UserRepository

# One email per address and purpose in this many seconds.
EMAIL_REQUEST_INTERVAL_SECONDS = 300

CONFIRMATION_LINK_INVALID = "This link is not valid or has expired. Send a new one."
RESET_LINK_INVALID = "This link is not valid or has expired. Ask for a new one."

CONFIRMATION_SUBJECT = "Confirm your Smart Survey email address"
CONFIRMATION_INTRO = "Confirm your email address for the Smart Survey Platform by opening this link:"
CONFIRMATION_OUTRO = (
    "The link works for 3 days. If you did not create an account, you can ignore this email."
)
RESET_SUBJECT = "Reset your Smart Survey password"
RESET_INTRO = "To choose a new password for the Smart Survey Platform, open this link:"
RESET_OUTRO = (
    "The link works for 3 days and only once. If you did not ask for a new password, "
    "you can ignore this email; your password stays the same."
)
SIGNATURE = "Smart Survey Platform"


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """Confirmation tokens: separate salt, and a token stops working once the email is confirmed."""

    key_salt = "services.account_email_service.EmailConfirmationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_confirmation_token = EmailConfirmationTokenGenerator()


class AccountEmailService:
    """FR-15: email confirmation before the first log-in, and password recovery by email."""

    def __init__(self, user_repository=None):
        self.user_repository = user_repository or UserRepository()

    def send_confirmation(self, account, base_url):
        """Email the confirmation link to a new account's address (no acting user)."""
        link = self._link(base_url, "users:confirm_email", account, email_confirmation_token)
        self._send(account, CONFIRMATION_SUBJECT, CONFIRMATION_INTRO, link, CONFIRMATION_OUTRO)

    def resend_confirmation(self, email, base_url):
        """Send a new link to an unconfirmed active account; silent for any other address."""
        user = self.user_repository.find_by_email(email)
        if user is None or user.email_verified or not self._is_active(user):
            return
        if not self._claim_slot("confirmation", email):
            return
        self.send_confirmation(user, base_url)

    def confirm_email(self, uidb64, token):
        """Mark the account's email as confirmed when the link is valid."""
        user = self._user_from_uid(uidb64)
        if user is None or not email_confirmation_token.check_token(user, token):
            raise ValidationError(CONFIRMATION_LINK_INVALID)
        user.email_verified = True
        return self.user_repository.update(user)

    def send_password_reset(self, email, base_url):
        """Email a reset link to an active account with a password; silent for any other address."""
        user = self.user_repository.find_by_email(email)
        if user is None or not self._is_active(user) or not user.has_usable_password():
            return
        if not self._claim_slot("password_reset", email):
            return
        link = self._link(base_url, "users:password_reset_confirm", user, default_token_generator)
        self._send(user, RESET_SUBJECT, RESET_INTRO, link, RESET_OUTRO)

    def check_password_reset_link(self, uidb64, token):
        """Return the link's user, or raise ValidationError when the link is not valid."""
        user = self._user_from_uid(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            raise ValidationError(RESET_LINK_INVALID)
        return user

    def reset_password(self, uidb64, token, password1, password2):
        """Set the new password, confirm the email and end every app session of the account."""
        user = self.check_password_reset_link(uidb64, token)
        if password1 != password2:
            raise ValidationError(SetPasswordForm.error_messages["password_mismatch"])
        try:
            validate_password(password1, user=user)
        except DjangoValidationError as err:
            raise ValidationError(" ".join(err.messages))

        with transaction.atomic():
            user.set_password(password1)
            # Opening a link sent to the address proves the owner reads it.
            user.email_verified = True
            self.user_repository.update(user)
            self.user_repository.blacklist_refresh_tokens(user)
        return user

    def _send(self, user, subject, intro, link, outro):
        body = "\n\n".join([f"Hello {user.name},", intro, link, outro, SIGNATURE])
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])

    def _link(self, base_url, route_name, user, token_generator):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        return urljoin(base_url, reverse(route_name, args=[uidb64, token]))

    def _user_from_uid(self, uidb64):
        try:
            user_id = int(force_str(urlsafe_base64_decode(uidb64)))
        except (TypeError, ValueError, OverflowError):
            return None
        return self.user_repository.find_by_id(user_id)

    def _claim_slot(self, purpose, email):
        """Return True at most once per address and purpose in the interval."""
        key = f"account_email:{purpose}:{email.strip().lower()}"
        return cache.add(key, True, EMAIL_REQUEST_INTERVAL_SECONDS)

    def _is_active(self, user):
        return user.is_active and user.account_status == AccountStatus.ACTIVE
