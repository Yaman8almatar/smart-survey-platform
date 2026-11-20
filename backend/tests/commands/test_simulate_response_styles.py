import re
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.core.models import (
    Answer,
    Question,
    RespondentProfile,
    Response,
    ResponseDraft,
    Survey,
    User,
)
from core.enums import QuestionType, SurveyStatus, UserType
from repositories.profile_repository import ProfileRepository
from services.quality_service import QualityService
from services.targeting_service import TargetingService

COMMAND = "simulate_response_styles"
DOMAIN = "@simulation.smartsurvey.test"
PROVIDER_EMAIL = "simulation-provider" + DOMAIN
PASSWORD = "simulation-pass"
P10_LINE = "Style injected against flag raised. Synthetic data, not a measure of accuracy (P-10)."

# The brief's table (TASK-45 B), in respondent-number order.
STYLE_TABLE = (
    ("careful", 20, set()),
    ("speeder", 3, {"SPEEDING"}),
    ("relative speeder", 3, {"SPEEDING"}),
    ("straight-liner", 2, {"STRAIGHT_LINING"}),
    ("inattentive", 2, {"ATTENTION_FAILED"}),
    ("shared device", 2, {"DUPLICATE_DEVICE"}),
    ("careless", 2, {"ATTENTION_FAILED", "SPEEDING", "STRAIGHT_LINING"}),
    ("evidence withheld", 2, {"SIGNALS_MISSING"}),
)
STYLE_BY_NUMBER = {
    number: (name, expected)
    for number, (name, expected) in enumerate(
        ((name, expected) for name, count, expected in STYLE_TABLE for _ in range(count)),
        start=1,
    )
}


def run(*args):
    out = StringIO()
    call_command(COMMAND, *args, stdout=out)
    return out.getvalue()


def simulate(*extra):
    with override_settings(DEBUG=True):
        return run("--provider-password", PASSWORD, *extra)


def number_of(user):
    return int(user.email.split("@")[0].removeprefix("sim-"))


def simulation_survey():
    return Survey.objects.get(provider__email=PROVIDER_EMAIL)


def make_ordinary_respondent(email):
    user = User.objects.create_user(
        email=email, password="strong-password", name="Real", user_type=UserType.RESPONDENT
    )
    RespondentProfile.objects.create(
        user=user, age=30, gender="FEMALE", region="DAMASCUS", interests=["HEALTH"]
    )
    return user


@pytest.mark.django_db
def test_every_response_raises_exactly_its_styles_flags():
    output = simulate()
    print(output)  # shown with pytest -s: the table the report quotes

    assert P10_LINE in output
    assert f"Provider: {PROVIDER_EMAIL}" in output
    survey = simulation_survey()
    provider = User.objects.get(email=PROVIDER_EMAIL)
    evaluation = QualityService().evaluate_survey(provider, survey.survey_id)

    respondent_by_response = {
        response.response_id: response.respondent
        for response in Response.objects.filter(survey=survey).select_related("respondent")
    }
    seen = set()
    for entry in evaluation["responses"]:
        number = number_of(respondent_by_response[entry["response_id"]])
        name, expected = STYLE_BY_NUMBER[number]
        assert set(entry["flags"]) == expected, (number, name, entry["flags"])
        seen.add(number)
    assert seen == set(range(1, 37))
    assert evaluation["band_counts"] == {"CLEAN": 20, "CHECK": 14, "LOW": 2}


@pytest.mark.django_db
def test_survey_is_closed_and_respondents_reach_no_one():
    make_ordinary_respondent("real@example.com")
    open_criteria = TargetingService().build_criteria()
    reach_before = ProfileRepository().count_matching(open_criteria)

    simulate()

    survey = simulation_survey()
    assert survey.status == SurveyStatus.CLOSED
    assert survey.title == "[Simulation] Response styles"
    assert Response.objects.filter(survey=survey).count() == 36
    questions = Question.objects.filter(survey=survey)
    assert questions.count() == 8
    assert not questions.filter(question_type=QuestionType.OPEN_TEXT).exists()
    attention = questions.get(is_attention_check=True)
    assert attention.expected_option.option_text == "Agree"
    assert not ResponseDraft.objects.exists()

    respondents = User.objects.filter(email__endswith=DOMAIN, user_type=UserType.RESPONDENT)
    assert respondents.count() == 36
    assert not respondents.filter(is_active=True).exists()
    provider = User.objects.get(email=PROVIDER_EMAIL)
    assert provider.is_active
    assert provider.user_type == UserType.SERVICE_PROVIDER
    assert provider.check_password(PASSWORD)
    assert ProfileRepository().count_matching(open_criteria) == reach_before


@pytest.mark.django_db
def test_start_mark_and_active_time_within_wall_time():
    simulate()

    responses = Response.objects.filter(survey=simulation_survey()).select_related(
        "respondent", "quality"
    )
    for response in responses:
        name, _ = STYLE_BY_NUMBER[number_of(response.respondent)]
        if name == "evidence withheld":
            assert response.started_at is None
            assert response.quality.active_ms is None
            assert response.quality.device_hash == ""
        else:
            assert response.started_at is not None
            wall_ms = (response.submitted_at - response.started_at).total_seconds() * 1000
            assert response.quality.active_ms <= wall_ms
            assert response.quality.signals_ok


def collect_run():
    """Return active_ms, ratings and device hashes by respondent number and question position."""
    survey = simulation_survey()
    position = dict(
        Question.objects.filter(survey=survey).values_list("question_id", "order_index")
    )
    timings, hashes = {}, {}
    for response in Response.objects.filter(survey=survey).select_related(
        "respondent", "quality"
    ):
        number = number_of(response.respondent)
        hashes[number] = response.quality.device_hash
        for timing in response.quality.timings:
            timings[(number, position[timing["question_id"]])] = timing["active_ms"]
    ratings = {
        (number_of(answer.response.respondent), answer.question.order_index): answer.rating_value
        for answer in Answer.objects.filter(response__survey=survey).select_related(
            "response__respondent", "question"
        )
    }
    return survey.survey_id, timings, ratings, hashes


@pytest.mark.django_db
def test_same_seed_gives_same_timings_ratings_and_devices():
    simulate("--seed", "7")
    first_id, first_timings, first_ratings, first_hashes = collect_run()
    run("--delete")
    simulate("--seed", "7")
    second_id, second_timings, second_ratings, second_hashes = collect_run()

    assert first_id != second_id
    assert len(first_timings) == 34 * 8
    assert first_timings == second_timings
    assert first_ratings == second_ratings
    assert first_hashes == second_hashes


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_refuses_without_debug():
    with pytest.raises(CommandError, match="DEBUG"):
        run("--provider-password", PASSWORD)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_refuses_a_second_run():
    simulate()
    with pytest.raises(CommandError, match="Simulation data exists. Run --delete first."):
        simulate()
    assert Survey.objects.count() == 1


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_refuses_a_short_or_missing_password():
    with pytest.raises(CommandError, match="at least 8"):
        run("--provider-password", "short77")
    with pytest.raises(CommandError, match="required"):
        run()
    assert not User.objects.exists()


@pytest.mark.django_db
def test_delete_without_debug_removes_only_the_simulation_domain():
    simulate()
    synthetic = make_ordinary_respondent("synthetic-0001@synthetic.smartsurvey.test")
    real = make_ordinary_respondent("real@example.com")
    owner = User.objects.create_user(
        email="owner@example.com",
        password="strong-password",
        name="Owner",
        user_type=UserType.SERVICE_PROVIDER,
    )
    real_survey = Survey.objects.create(provider=owner, title="Real survey", description="")
    real_response = Response.objects.create(survey=real_survey, respondent=real)

    with override_settings(DEBUG=False):
        output = run("--delete")

    assert "Deleted simulation users: 37, surveys: 1, responses: 36." in output
    assert not User.objects.filter(email__endswith=DOMAIN).exists()
    assert set(Survey.objects.all()) == {real_survey}
    assert list(Response.objects.all()) == [real_response]
    assert set(User.objects.all()) == {synthetic, real, owner}


@pytest.mark.django_db
def test_output_holds_no_hash_or_device_id():
    output = simulate()

    assert re.search(r"[0-9a-f]{32}", output) is None
    assert "active_ms" not in output
