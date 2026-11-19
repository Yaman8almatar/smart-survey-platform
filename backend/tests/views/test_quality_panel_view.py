"""TASK-43 (board W-04): the "Response quality" panel of the analytics page.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import re

import pytest
from django.urls import reverse

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    Response,
    ResponseQuality,
    Survey,
    User,
)
from core.enums import AccountStatus, QuestionType, SurveyStatus, UserType

pytestmark = pytest.mark.django_db

TITLE = "Response quality"
NO_FLAG = "No response is flagged."
FOOTER = "Flagged responses are kept. You decide which ones count."
CAPTION = (
    "Charts, summaries and the export count included responses only. Speed says little on "
    "factual questions, where people who know the answer are quick."
)
NAMES = {
    "ATTENTION_FAILED": "Failed attention check",
    "SPEEDING": "Answered very fast",
    "DUPLICATE_DEVICE": "Same device as another account",
    "STRAIGHT_LINING": "Same rating on every rating question",
    "SIGNALS_MISSING": "Timing or device data missing",
}
NOT_CHECKED = {
    "ATTENTION_FAILED": "Not checked: this survey has no attention check.",
    "SPEEDING": "Not checked: needs at least 3 answered closed questions.",
    "STRAIGHT_LINING": "Not checked: needs 5 or more rating questions.",
}


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return make_user("provider-quality@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    """Published survey: one choice and two ratings, three closed questions."""
    survey = Survey.objects.create(provider=provider, title="Quality", status=SurveyStatus.PUBLISHED)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="B", order_index=1)
    for index in (1, 2):
        Question.objects.create(
            survey=survey,
            question_text=f"Rate {index}",
            question_type=QuestionType.RATING_SCALE,
            order_index=index,
        )
    return survey


def add_response(
    survey,
    evidence=True,
    active_ms=5_000,
    timed=True,
    signals_ok=True,
    attention_total=0,
    attention_failed=0,
    rating_count=2,
    device_hash="",
    excluded=False,
):
    """Store one response that answered every question; a default one has no flag."""
    index = Response.objects.count()
    respondent = make_user(f"respondent-quality-{index}@example.com", UserType.RESPONDENT)
    response = Response.objects.create(survey=survey, respondent=respondent, is_excluded=excluded)
    questions = list(survey.questions.order_by("order_index"))
    for question in questions:
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            Answer.objects.create(
                response=response, question=question, selected_option=question.options.first()
            )
        else:
            Answer.objects.create(response=response, question=question, rating_value=3)
    if evidence:
        timings = (
            [{"question_id": q.question_id, "active_ms": active_ms} for q in questions]
            if timed
            else []
        )
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=timings,
            active_ms=active_ms * len(questions) if timed else None,
            attention_total=attention_total,
            attention_failed=attention_failed,
            rating_count=rating_count,
            rating_all_same=True,
            device_hash=device_hash,
            signals_ok=signals_ok,
        )
    return response


def add_responses(survey, count, **kwargs):
    return [add_response(survey, **kwargs) for _ in range(count)]


def dashboard(client, provider, survey):
    client.force_login(provider)
    response = client.get(reverse("analysis:analytics_dashboard", args=[survey.survey_id]))
    assert response.status_code == 200
    return response.content.decode()


def panel(content):
    start = content.index(f'<h2 class="section-title mb-0">{TITLE}</h2>')
    return content[start:content.index("<!-- Analytics charts -->")]


def table_rows(content):
    """Return the body rows of the flags table as lists of cell texts."""
    return [
        re.findall(r"<td>(.*?)</td>", row, re.S)
        for row in re.findall(r"<tr[^>]*>.*?</tr>", panel(content), re.S)
    ][1:]


def band_count(content, name):
    match = re.search(
        rf"</span>{name}</span>\s*<strong>(\d+)</strong>", panel(content)
    )
    return int(match.group(1))


def test_the_panel_is_absent_while_the_results_are_locked(client, provider, survey):
    add_responses(survey, 4)

    content = dashboard(client, provider, survey)

    assert TITLE not in content
    assert reverse("analysis:exclude_flagged", args=[survey.survey_id]) not in content


def test_header_version_and_count_line_sit_between_metrics_and_sentiment(
    client, provider, survey
):
    add_responses(survey, 5)

    content = dashboard(client, provider, survey)

    assert "Rules version 1" in panel(content)
    assert "<strong>5 of 5</strong> responses included.</p>" in content
    assert content.index("metric-card") < content.index(TITLE)
    assert content.index(TITLE) < content.index("Sentiment of open answers")


def test_the_count_line_adds_the_excluded(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, excluded=True)

    content = dashboard(client, provider, survey)

    assert "<strong>4 of 5</strong> responses included. 1 excluded.</p>" in content
    assert "<small>4 included</small>" in content


def test_band_tiles_hold_the_band_counts(client, provider, survey):
    add_responses(survey, 3)
    add_response(survey, rating_count=5)  # straight-lining: 90, CHECK
    add_response(survey, attention_total=1, attention_failed=1, signals_ok=False)  # 30, LOW

    content = dashboard(client, provider, survey)

    assert (band_count(content, "Clean"), band_count(content, "Check"), band_count(content, "Low")) == (3, 1, 1)
    section = panel(content)
    assert section.index("No flag") < section.index("Score 60 to 99") < section.index("Score under 60")


def test_flag_rows_follow_the_board_order_with_their_meanings(client, provider, survey):
    add_response(survey, signals_ok=False)
    add_response(survey, rating_count=5)
    add_response(survey, device_hash="d" * 64)
    add_response(survey, device_hash="d" * 64)
    add_response(survey, active_ms=500)
    add_response(survey, attention_total=1, attention_failed=1)

    rows = table_rows(dashboard(client, provider, survey))

    assert [row[0] for row in rows] == list(NAMES.values())
    assert [row[2] for row in rows] == ["1", "1", "2", "1", "1"]
    assert all(row[1] and not row[1].startswith("Not checked") for row in rows)


def test_flag_rows_stay_after_an_exclusion(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, attention_total=1, attention_failed=1, excluded=True)

    content = dashboard(client, provider, survey)

    assert NAMES["ATTENTION_FAILED"] in panel(content)
    assert NO_FLAG not in content


def test_not_checked_rows_follow_the_flag_rows(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, active_ms=500)

    rows = table_rows(dashboard(client, provider, survey))

    assert rows == [
        [NAMES["SPEEDING"], rows[0][1], "1"],
        [NAMES["ATTENTION_FAILED"], NOT_CHECKED["ATTENTION_FAILED"], "&ndash;"],
        [NAMES["STRAIGHT_LINING"], NOT_CHECKED["STRAIGHT_LINING"], "&ndash;"],
    ]


def test_answered_very_fast_not_checked_row_when_no_response_has_closed_timings(
    client, provider, survey
):
    add_responses(survey, 5, timed=False)

    content = dashboard(client, provider, survey)

    assert NOT_CHECKED["SPEEDING"] in content
    assert NO_FLAG in content


def test_no_answered_very_fast_row_when_every_response_lacks_its_timings(
    client, provider, survey
):
    add_responses(survey, 5, timed=False, signals_ok=False)

    rows = table_rows(dashboard(client, provider, survey))

    assert rows[0] == [NAMES["SIGNALS_MISSING"], rows[0][1], "5"]
    assert NAMES["SPEEDING"] not in [row[0] for row in rows]


def test_never_a_same_device_not_checked_row(client, provider, survey):
    add_responses(survey, 5)

    content = dashboard(client, provider, survey)

    assert NAMES["DUPLICATE_DEVICE"] not in content
    assert NAMES["SIGNALS_MISSING"] not in content


def test_a_not_checked_row_needs_every_evaluated_response(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, rating_count=5, attention_total=1)  # straight-lining flagged

    content = dashboard(client, provider, survey)

    assert NOT_CHECKED["ATTENTION_FAILED"] not in content
    assert NOT_CHECKED["STRAIGHT_LINING"] not in content


def test_the_before_checks_note_in_plural(client, provider, survey):
    add_responses(survey, 3)
    add_responses(survey, 2, evidence=False)

    content = dashboard(client, provider, survey)

    assert (
        "<strong>2 responses were collected before quality checks.</strong> "
        "They have no score and stay included."
    ) in content


def test_the_before_checks_note_in_singular(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, evidence=False)

    content = dashboard(client, provider, survey)

    assert (
        "<strong>1 response was collected before quality checks.</strong> "
        "It has no score and stays included."
    ) in content


def test_no_before_checks_note_without_such_responses(client, provider, survey):
    add_responses(survey, 5)

    assert "collected before quality checks" not in dashboard(client, provider, survey)


def test_nothing_flagged_disables_both_actions(client, provider, survey):
    add_responses(survey, 5)

    content = dashboard(client, provider, survey)
    section = panel(content)

    assert NO_FLAG in section
    assert re.search(
        r'<button type="button" class="btn btn-outline-danger" disabled>'
        r"<i[^>]*></i>Exclude flagged responses</button>",
        section,
    )
    assert re.search(
        r'<button type="button" class="btn btn-outline-secondary" disabled>'
        r"<i[^>]*></i>Include all</button>",
        section,
    )
    assert reverse("analysis:exclude_flagged", args=[survey.survey_id]) not in content
    assert reverse("analysis:include_all", args=[survey.survey_id]) not in content
    assert FOOTER in section
    assert CAPTION in section


def test_the_action_labels_carry_n_and_e(client, provider, survey):
    add_responses(survey, 2)
    add_responses(survey, 2, attention_total=1, attention_failed=1)
    add_response(survey, excluded=True)

    content = dashboard(client, provider, survey)

    exclude_url = reverse("analysis:exclude_flagged", args=[survey.survey_id])
    include_url = reverse("analysis:include_all", args=[survey.survey_id])
    assert re.search(
        rf'<a class="btn btn-outline-danger" href="{exclude_url}"><i[^>]*></i>'
        r"Exclude flagged responses \(2\)</a>",
        content,
    )
    assert re.search(
        rf'<a class="btn btn-outline-secondary" href="{include_url}"><i[^>]*></i>'
        r"Include all \(1 excluded\)</a>",
        content,
    )
    assert NO_FLAG not in content


def test_an_attention_question_is_not_in_question_results(client, provider, survey):
    add_responses(survey, 5)
    check = Question.objects.create(
        survey=survey,
        question_text="Choose 5 to show you are reading",
        question_type=QuestionType.RATING_SCALE,
        order_index=3,
        is_required=True,
        is_attention_check=True,
        expected_rating=5,
    )
    for response in Response.objects.filter(survey=survey):
        Answer.objects.create(response=response, question=check, rating_value=5)

    content = dashboard(client, provider, survey)

    assert "Question results" in content
    assert check.question_text not in content
