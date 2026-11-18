from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.core.models import RespondentProfile, User
from core.enums import AccountStatus, UserType
from repositories.profile_repository import ProfileRepository

COMMAND = "create_synthetic_respondents"
DOMAIN = "@synthetic.smartsurvey.test"


def run(*args):
    out = StringIO()
    call_command(COMMAND, *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_refuses_without_debug():
    with pytest.raises(CommandError, match="DEBUG"):
        run("--count", "3")
    assert not User.objects.exists()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_creates_complete_labelled_respondents_once():
    output = run("--count", "20")

    assert "Created 20 synthetic respondents" in output
    users = User.objects.filter(email__endswith=DOMAIN).order_by("email")
    assert users.count() == 20
    first = users.first()
    assert first.email == "synthetic-0001" + DOMAIN
    assert first.name == "Synthetic respondent 0001"
    assert not first.has_usable_password()
    assert {(user.user_type, user.account_status) for user in users} == {
        (UserType.RESPONDENT, AccountStatus.ACTIVE)
    }
    assert all(profile.is_complete() for profile in RespondentProfile.objects.all())
    assert ProfileRepository().count_pool() == 20

    assert "Created 0 synthetic respondents" in run("--count", "20")
    assert User.objects.count() == 20


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_delete_removes_only_the_synthetic_domain():
    run("--count", "5")
    kept = [
        User.objects.create_user(
            email=email, password="strong-password", name="Kept", user_type=UserType.RESPONDENT
        )
        for email in ("real@example.com", "someone@notsynthetic.smartsurvey.test")
    ]

    output = run("--delete")

    assert "Deleted 5 synthetic respondents" in output
    assert set(User.objects.all()) == set(kept)
    assert not RespondentProfile.objects.exists()
