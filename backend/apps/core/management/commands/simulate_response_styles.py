import random
from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.models import RespondentProfile, Response, ResponseDraft, Survey, User
from core.enums import (
    AccountStatus,
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    QuestionType,
    UserType,
)
from services import quality_rules
from services.quality_rules import (
    ATTENTION_FAILED,
    DUPLICATE_DEVICE,
    SIGNALS_MISSING,
    SPEEDING,
    STRAIGHT_LINING,
)
from services.quality_service import QualityService
from services.question_service import QuestionService
from services.response_service import ResponseService
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService
from services.targeting_service import TargetingService

DOMAIN = "simulation.smartsurvey.test"
PROVIDER_EMAIL = f"simulation-provider@{DOMAIN}"
ADMIN_EMAIL = f"simulation-admin@{DOMAIN}"
MIN_PASSWORD_LENGTH = 8
PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

SURVEY_TITLE = "[Simulation] Response styles"
SURVEY_DESCRIPTION = (
    "Synthetic responses with known styles, made by simulate_response_styles. Not real data."
)
TRANSPORT_TEXT = "How often do you use public transport?"
TRANSPORT_OPTIONS = ["Daily", "Weekly", "Monthly", "Rarely"]
ATTENTION_TEXT = 'To show that you are reading, choose "Agree" for this question.'
ATTENTION_OPTIONS = ["Agree", "Neutral", "Disagree"]
RATING_COUNT = 6
QUESTION_COUNT = 2 + RATING_COUNT

BASE_MS = (6_000, 9_000)  # base time of each question, drawn once per run
CAREFUL_FACTOR = (0.8, 1.25)
SPEEDER_MS = (600, 1_500)
RELATIVE_SPEED_DIVISOR = 2.8  # b_q / 2.8 is 2,143 to 3,214 ms: never under the 2 s floor
STRAIGHT_RATING = 3
# Wall time beyond the summed active time, so the server's wall-time check holds.
WALL_MARGIN = timedelta(seconds=60)

# timing: "careful", "speeder", "relative" or None (no evidence sent).
STYLES = (
    {"name": "careful", "count": 20, "timing": "careful", "straight": False,
     "attention": "Agree", "shared": False, "expected": ()},
    {"name": "speeder", "count": 3, "timing": "speeder", "straight": False,
     "attention": "Agree", "shared": False, "expected": (SPEEDING,)},
    {"name": "relative speeder", "count": 3, "timing": "relative", "straight": False,
     "attention": "Agree", "shared": False, "expected": (SPEEDING,)},
    {"name": "straight-liner", "count": 2, "timing": "careful", "straight": True,
     "attention": "Agree", "shared": False, "expected": (STRAIGHT_LINING,)},
    {"name": "inattentive", "count": 2, "timing": "careful", "straight": False,
     "attention": "Disagree", "shared": False, "expected": (ATTENTION_FAILED,)},
    {"name": "shared device", "count": 2, "timing": "careful", "straight": False,
     "attention": "Agree", "shared": True, "expected": (DUPLICATE_DEVICE,)},
    {"name": "careless", "count": 2, "timing": "speeder", "straight": True,
     "attention": "Disagree", "shared": False,
     "expected": (ATTENTION_FAILED, SPEEDING, STRAIGHT_LINING)},
    {"name": "evidence withheld", "count": 2, "timing": None, "straight": False,
     "attention": "Agree", "shared": False, "expected": (SIGNALS_MISSING,)},
)

P10_LINE = "Style injected against flag raised. Synthetic data, not a measure of accuracy (P-10)."


class Command(BaseCommand):
    """Submits labelled synthetic responses with known styles and reports the flags (P-10)."""

    help = (
        "Build one closed '[Simulation]' survey owned by " + PROVIDER_EMAIL + " and answer it "
        "with 36 SYNTHETIC respondents (sim-NNN@" + DOMAIN + ") in eight known response "
        "styles, through the real services. Prints the style injected against the flags "
        "raised and fails if any response differs from its style. Synthetic only (P-10). "
        "A run needs DEBUG on; --delete runs on any database."
    )

    def add_arguments(self, parser):
        """Declare the command options."""
        parser.add_argument(
            "--provider-password",
            help=f"Password of the simulation provider (at least {MIN_PASSWORD_LENGTH} characters).",
        )
        parser.add_argument("--seed", type=int, default=4, help="Random seed (default 4).")
        parser.add_argument(
            "--delete",
            action="store_true",
            help=f"Delete every user whose email ends in @{DOMAIN}, and nothing else.",
        )

    def handle(self, *args, **options):
        """Run the simulation, or delete its data with --delete."""
        # The cleanup must work on any database, so --delete skips the DEBUG check.
        if options["delete"]:
            self._delete()
            return

        if not settings.DEBUG:
            raise CommandError("simulate_response_styles runs only with DEBUG on.")
        password = options["provider_password"]
        if not password:
            raise CommandError("--provider-password is required for a run.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise CommandError(
                f"--provider-password must have at least {MIN_PASSWORD_LENGTH} characters."
            )
        if User.objects.filter(email__iendswith=f"@{DOMAIN}").exists():
            raise CommandError("Simulation data exists. Run --delete first.")

        rng = random.Random(options["seed"])
        # One transaction: a failure part-way leaves no simulation data behind.
        with transaction.atomic():
            provider = self._create_provider(password)
            survey_id, questions = self._build_survey(provider)
            respondents = self._create_respondents(rng)
            style_by_response = self._submit_all(rng, survey_id, questions, respondents)
            SurveyService().close_survey(provider, survey_id)
            # No simulation respondent counts in a reach or can sign in.
            User.objects.filter(
                email__iendswith=f"@{DOMAIN}", user_type=UserType.RESPONDENT
            ).update(is_active=False)

        evaluation = QualityService().evaluate_survey(provider, survey_id)
        self._report(survey_id, evaluation, style_by_response)

    def _delete(self):
        """Delete every simulation user; the cascade removes their survey and responses."""
        users = User.objects.filter(email__iendswith=f"@{DOMAIN}")
        user_count = users.count()
        survey_count = Survey.objects.filter(provider__in=users).count()
        response_count = Response.objects.filter(respondent__in=users).count()
        users.delete()
        self.stdout.write(
            f"Deleted simulation users: {user_count}, surveys: {survey_count}, "
            f"responses: {response_count}."
        )

    def _create_provider(self, password):
        """Create the labelled simulation provider."""
        return User.objects.create_user(
            email=PROVIDER_EMAIL,
            password=password,
            name="Simulation provider",
            user_type=UserType.SERVICE_PROVIDER,
            account_status=AccountStatus.ACTIVE,
        )

    def _create_admin(self):
        """Create the labelled simulation admin that approves the survey; it cannot sign in."""
        admin = User(
            email=ADMIN_EMAIL,
            name="Simulation admin",
            user_type=UserType.ADMIN,
            account_status=AccountStatus.ACTIVE,
            is_active=True,
        )
        admin.set_unusable_password()
        admin.save()
        return admin

    def _build_survey(self, provider):
        """Create, target, submit and approve the survey through the services.

        Returns the survey id and the questions in order as
        (question_id, question_type, {option text: option id}).
        """
        survey_id = SurveyService().create_survey(
            provider, SURVEY_TITLE, SURVEY_DESCRIPTION
        ).survey_id

        question_service = QuestionService()
        question_service.add_question_with_options(
            provider, survey_id, TRANSPORT_TEXT, QuestionType.MULTIPLE_CHOICE, True, 0,
            options=TRANSPORT_OPTIONS,
        )
        question_service.add_question_with_options(
            provider, survey_id, ATTENTION_TEXT, QuestionType.MULTIPLE_CHOICE, True, 1,
            options=ATTENTION_OPTIONS,
            is_attention_check=True,
            expected_option_index=ATTENTION_OPTIONS.index("Agree"),
        )
        for number in range(1, RATING_COUNT + 1):
            question_service.add_question_with_options(
                provider, survey_id, f"Rate statement {number}.", QuestionType.RATING_SCALE,
                True, 1 + number,
            )

        TargetingService().save_criteria(provider, survey_id)
        # FR-12: a survey is published only through an admin's approval.
        SurveyService().submit_for_review(provider, survey_id)
        SurveyReviewService().approve(self._create_admin(), survey_id)

        questions = [
            (
                row["question_id"],
                row["question_type"],
                {option["option_text"]: option["option_id"] for option in row["options"]},
            )
            for row in question_service.get_survey_question_rows(provider, survey_id)
        ]
        return survey_id, questions

    def _create_respondents(self, rng):
        """Create sim-001..sim-036 with complete profiles; return (user, style) in order."""
        styles = [style for style in STYLES for _ in range(style["count"])]
        users, profiles = [], []
        for number, _style in enumerate(styles, start=1):
            user = User(
                email=f"sim-{number:03d}@{DOMAIN}",
                name=f"Simulation respondent {number:03d}",
                user_type=UserType.RESPONDENT,
                account_status=AccountStatus.ACTIVE,
            )
            user.set_unusable_password()
            users.append(user)
            profiles.append(self._draw_profile(rng))

        users = User.objects.bulk_create(users)
        RespondentProfile.objects.bulk_create(
            RespondentProfile(user=user, **values) for user, values in zip(users, profiles)
        )
        return list(zip(users, styles))

    def _draw_profile(self, rng):
        """Return complete profile values: every one of the seven details filled."""
        return {
            "age": rng.randint(18, 70),
            "gender": rng.choice([Gender.MALE, Gender.FEMALE]),
            "region": rng.choice(Governorate.values),
            "interests": rng.sample(Interest.values, rng.randint(1, 3)),
            "education": self._detail(rng, Education),
            "occupation": self._detail(rng, Occupation),
            "marital_status": self._detail(rng, MaritalStatus),
        }

    def _detail(self, rng, enum):
        """Return one real value of an optional profile detail."""
        return rng.choice([value for value in enum.values if value != PREFER_NOT_TO_SAY])

    def _submit_all(self, rng, survey_id, questions, respondents):
        """Send every response through ResponseService; return {response_id: style}."""
        base_ms = [rng.randint(*BASE_MS) for _ in questions]
        shared_device_id = self._device_id(rng)
        service = ResponseService()

        style_by_response = {}
        for user, style in respondents:
            answers = self._answers(rng, questions, style)
            if style["timing"] is None:
                # An app before FR-04: no start mark, no timings, no device id.
                response = service.submit_response(user, survey_id, answers)
            else:
                device_id = shared_device_id if style["shared"] else self._device_id(rng)
                timings = [
                    {"question_id": question_id, "active_ms": active_ms}
                    for (question_id, _, _), active_ms in zip(
                        questions, self._timings(rng, style["timing"], base_ms)
                    )
                ]
                service.save_draft(user, survey_id, [], timings=[])
                # The simulation has no real minutes to wait, and the server checks the active
                # time against its own clock (planning/API.md "Quality signals"), so the start
                # mark is moved back by the summed active time plus a margin.
                wall = timedelta(milliseconds=sum(t["active_ms"] for t in timings)) + WALL_MARGIN
                ResponseDraft.objects.filter(survey_id=survey_id, respondent=user).update(
                    started_at=timezone.now() - wall
                )
                response = service.submit_response(user, survey_id, answers, timings, device_id)
            style_by_response[response.response_id] = (user, style)
        return style_by_response

    def _device_id(self, rng):
        """Return 32 lowercase hex characters from the seeded generator."""
        return f"{rng.getrandbits(128):032x}"

    def _timings(self, rng, kind, base_ms):
        """Return the whole-millisecond active time of every question for a timing kind."""
        if kind == "speeder":
            return [rng.randint(*SPEEDER_MS) for _ in base_ms]
        if kind == "relative":
            return [round(base / RELATIVE_SPEED_DIVISOR) for base in base_ms]
        return [round(base * rng.uniform(*CAREFUL_FACTOR)) for base in base_ms]

    def _answers(self, rng, questions, style):
        """Return the answers of one response in its style."""
        (transport_id, _, transport_options), (attention_id, _, attention_options) = questions[:2]
        rating_ids = [question_id for question_id, _, _ in questions[2:]]

        if style["straight"]:
            ratings = [STRAIGHT_RATING] * len(rating_ids)
        else:
            # Careful ratings use at least two different values, so none is a straight line.
            ratings = [rng.randint(1, 5) for _ in rating_ids]
            while len(set(ratings)) < 2:
                ratings = [rng.randint(1, 5) for _ in rating_ids]

        return [
            {"question_id": transport_id,
             "selected_option_id": transport_options[rng.choice(TRANSPORT_OPTIONS)]},
            {"question_id": attention_id,
             "selected_option_id": attention_options[style["attention"]]},
            *(
                {"question_id": question_id, "rating_value": rating}
                for question_id, rating in zip(rating_ids, ratings)
            ),
        ]

    def _report(self, survey_id, evaluation, style_by_response):
        """Print the table of style against flags; fail if any response differs."""
        if evaluation["locked"]:
            raise CommandError("The simulation survey's results are locked.")

        tallies = {
            style["name"]: {"count": 0, "flags": Counter(), "bands": Counter()}
            for style in STYLES
        }
        mismatches = []
        for entry in evaluation["responses"]:
            user, style = style_by_response[entry["response_id"]]
            tally = tallies[style["name"]]
            tally["count"] += 1
            tally["flags"].update(entry["flags"])
            tally["bands"][entry["band"]] += 1
            if set(entry["flags"]) != set(style["expected"]):
                mismatches.append((user.email.split("@")[0], style, entry["flags"]))

        header = ["Style", "Count", "Expected flags", "Flags raised"] + [
            band.capitalize() for band in quality_rules.BANDS
        ]
        rows = [header]
        for style in STYLES:
            tally = tallies[style["name"]]
            raised = ", ".join(
                f"{code} {tally['flags'][code]}"
                for code in quality_rules.FLAG_CODES
                if tally["flags"][code]
            )
            rows.append(
                [
                    style["name"],
                    str(tally["count"]),
                    ", ".join(style["expected"]) or "none",
                    raised or "none",
                ]
                + [str(tally["bands"][band]) for band in quality_rules.BANDS]
            )

        widths = [max(len(row[column]) for row in rows) for column in range(len(header))]
        self.stdout.write(f"Simulation survey id: {survey_id}")
        self.stdout.write(f"Provider: {PROVIDER_EMAIL}")
        for row in rows:
            cells = [
                cell.rjust(width) if column == 1 or column >= 4 else cell.ljust(width)
                for column, (cell, width) in enumerate(zip(row, widths))
            ]
            self.stdout.write("  ".join(cells).rstrip())
        self.stdout.write(P10_LINE)

        if mismatches:
            for label, style, flags in mismatches:
                self.stdout.write(
                    f"Difference: {label} ({style['name']}) expected "
                    f"{', '.join(style['expected']) or 'none'}, raised {', '.join(flags) or 'none'}."
                )
            raise CommandError(
                f"{len(mismatches)} responses raised flags that differ from their style."
            )
