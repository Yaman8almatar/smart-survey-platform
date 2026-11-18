import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import RespondentProfile, User
from core.enums import (
    AccountStatus,
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    UserType,
)

DOMAIN = "synthetic.smartsurvey.test"
PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class Command(BaseCommand):
    """Fills a development database with labelled synthetic respondents (P-10)."""

    help = (
        "Create SYNTHETIC respondent accounts (synthetic-NNNN@" + DOMAIN + ") for the "
        "FR-03 reach demonstration only. They are not real people. Delete them with "
        "--delete before any measurement with real respondents (P-10). Runs only with DEBUG on."
    )

    def add_arguments(self, parser):
        """Declare the command options."""
        parser.add_argument(
            "--count", type=int, default=500, help="Accounts to create (default 500)."
        )
        parser.add_argument(
            "--seed", type=int, default=20261118, help="Random seed (default 20261118)."
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help=f"Delete every user whose email ends in @{DOMAIN}, and nothing else.",
        )

    def handle(self, *args, **options):
        """Create the synthetic respondents, or delete them with --delete."""
        if not settings.DEBUG:
            raise CommandError("create_synthetic_respondents runs only with DEBUG on.")

        if options["delete"]:
            synthetic = User.objects.filter(email__iendswith=f"@{DOMAIN}")
            deleted = synthetic.count()
            synthetic.delete()
            self.stdout.write(f"Deleted {deleted} synthetic respondents.")
            return

        count = options["count"]
        if count < 0:
            raise CommandError("--count must not be negative.")

        created = self._create(count, random.Random(options["seed"]))
        self.stdout.write(
            f"Created {created} synthetic respondents ({count - created} already existed)."
        )

    def _create(self, count, rng):
        """Create the missing accounts 1..count with complete profiles; return how many."""
        existing = set(
            User.objects.filter(email__iendswith=f"@{DOMAIN}").values_list("email", flat=True)
        )
        users, profile_values = [], []
        for number in range(1, count + 1):
            # Draw for every number so a profile does not depend on which accounts exist.
            values = self._draw_profile(rng)
            email = f"synthetic-{number:04d}@{DOMAIN}"
            if email in existing:
                continue
            user = User(
                email=email,
                name=f"Synthetic respondent {number:04d}",
                user_type=UserType.RESPONDENT,
                account_status=AccountStatus.ACTIVE,
            )
            user.set_unusable_password()
            users.append(user)
            profile_values.append(values)

        with transaction.atomic():
            users = User.objects.bulk_create(users)
            RespondentProfile.objects.bulk_create(
                RespondentProfile(user=user, **values)
                for user, values in zip(users, profile_values)
            )
        return len(users)

    def _draw_profile(self, rng):
        """Return complete profile values drawn with rng."""
        return {
            "age": rng.randint(16, 75),
            "gender": rng.choice([value for value in Gender.values if value != Gender.ANY]),
            "region": rng.choice(Governorate.values),
            "interests": rng.sample(Interest.values, rng.randint(1, 4)),
            "education": self._draw_detail(rng, Education),
            "occupation": self._draw_detail(rng, Occupation),
            "marital_status": self._draw_detail(rng, MaritalStatus),
        }

    def _draw_detail(self, rng, enum):
        """An optional detail: empty a quarter, PREFER_NOT_TO_SAY an eighth, else a value."""
        draw = rng.random()
        if draw < 0.25:
            return ""
        if draw < 0.375:
            return PREFER_NOT_TO_SAY
        return rng.choice([value for value in enum.values if value != PREFER_NOT_TO_SAY])
