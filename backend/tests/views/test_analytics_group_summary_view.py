"""W-05b: sentiment per open question and the group breakdown of the analytics page (TASK-48).

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5).
"""

import re

import pytest
from django.urls import reverse

from apps.core.models import Answer, Question, Response, SentimentAnalysisResult, Survey, User
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository

CARD_TITLE = '<h2 class="section-title">Group breakdown</h2>'
HELPER = (
    "Groups come from each respondent's profile when they answered. "
    "Groups with fewer than 5 answers are combined."
)
NOT_ANALYSED = "No answers to this question have been analysed yet."
NOT_ENOUGH = "Not enough responses to show this breakdown."
CAPTION = "Shares of the analysed answers in each group."

POSITIVE = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.POSITIVE})
NEUTRAL = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.NEUTRAL})
NEGATIVE = (AnalysisStatus.COMPLETED, {"sentiment_label": SentimentLabel.NEGATIVE})
PENDING = (AnalysisStatus.PENDING, {})


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey(entries):
    """Create a survey with one open-text question; each entry is (snapshot fields, result).

    result is (status, fields) of the answer's sentiment result, or None for no result.
    """
    provider = create_user("provider-groups@example.com", UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text="Any comments?",
            question_type=QuestionType.OPEN_TEXT,
            is_required=True,
            order_index=0,
        )
    )
    for index, (snapshot, result) in enumerate(entries):
        respondent = create_user(f"respondent-groups-{index}@example.com", UserType.RESPONDENT)
        response = ResponseRepository().save(
            Response(survey=survey, respondent=respondent, **snapshot)
        )
        answer = ResponseRepository().save_answer(
            Answer(response=response, question=question, answer_value=f"Answer {index}")
        )
        if result is not None:
            status, fields = result
            SentimentAnalysisResult.objects.create(answer=answer, status=status, **fields)
    return provider, survey


def get_dashboard(client, provider, survey, group_by=None):
    client.force_login(provider)
    url = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    data = {} if group_by is None else {"group_by": group_by}
    return client.get(url, data).content.decode()


def region(code, result, count):
    return [({"snap_region": code}, result)] * count


@pytest.mark.django_db
def test_group_breakdown_card_replaces_the_analytics_summary_card(client):
    provider, survey = create_survey([({}, POSITIVE)] * 5)

    content = get_dashboard(client, provider, survey)

    assert CARD_TITLE in content
    assert HELPER in content
    assert "Analytics summary</h2>" not in content
    action = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    assert re.search(rf'<form method="get" action="{action}"', content)
    assert '<label class="form-label" for="group-by-select">Compare groups by</label>' in content
    assert re.search(r'<select[^>]*id="group-by-select"[^>]*name="group_by"', content)
    options = re.findall(r'<option value="([^"]*)"( selected)?>([^<]*)</option>', content)
    assert options == [
        ("", " selected", "No breakdown"),
        ("gender", "", "Gender"),
        ("age", "", "Age group"),
        ("governorate", "", "Governorate"),
    ]
    assert '<button type="submit" class="btn btn-outline-secondary">Show</button>' in content


@pytest.mark.django_db
def test_question_shows_its_count_line_bar_and_legend(client):
    provider, survey = create_survey(
        [({}, POSITIVE)] * 3 + [({}, NEUTRAL), ({}, NEGATIVE), ({}, PENDING)]
    )

    content = get_dashboard(client, provider, survey)

    assert "Analysed 5 of 6 answers.</p>" in content
    assert 'role="img" aria-label="5 analysed answers: 3 positive, 1 neutral, 1 negative"' in content
    assert 'sentiment-swatch-positive" style="width: 60%"' in content
    assert 'sentiment-swatch-neutral" style="width: 20%"' in content
    assert "Positive 3 · 60%</li>" in content
    assert "Neutral 1 · 20%</li>" in content
    assert "Negative 1 · 20%</li>" in content
    # Without a dimension the question has no group table.
    assert "By governorate" not in content
    assert "group-breakdown-table" not in content


@pytest.mark.django_db
def test_governorate_breakdown_pools_small_groups_and_keeps_the_choice_selected(client):
    entries = (
        region("DAMASCUS", POSITIVE, 6)
        + region("ALEPPO", NEGATIVE, 5)
        + region("HOMS", POSITIVE, 3)
        + region("HAMA", NEUTRAL, 2)
    )
    provider, survey = create_survey(entries)

    content = get_dashboard(client, provider, survey, group_by="governorate")

    assert '<option value="governorate" selected>Governorate</option>' in content
    assert '<option value="" selected>' not in content
    assert "By governorate</h4>" in content
    for header in ("Group", "Analysed", "Positive", "Neutral", "Negative"):
        assert f'<th scope="col">{header}</th>' in content
    rows = re.findall(r'<th scope="row">([^<]*)</th>\s*<td>(\d+)</td>', content)
    assert rows == [("Damascus", "6"), ("Aleppo", "5"), ("Other groups (combined)", "5")]
    assert "Homs" not in content.split("group-breakdown-table", 1)[1].split("</table>", 1)[0]
    assert '3 <span class="group-breakdown-table__share">60%</span>' in content
    assert '2 <span class="group-breakdown-table__share">40%</span>' in content
    assert CAPTION in content
    assert NOT_ENOUGH not in content


@pytest.mark.django_db
def test_breakdown_with_one_row_left_shows_the_not_enough_line(client):
    provider, survey = create_survey(region("DAMASCUS", POSITIVE, 6) + region("HOMS", NEGATIVE, 2))

    content = get_dashboard(client, provider, survey, group_by="governorate")

    assert "By governorate</h4>" in content
    assert NOT_ENOUGH in content
    assert "group-breakdown-table" not in content
    assert CAPTION not in content


@pytest.mark.django_db
def test_question_with_nothing_analysed_shows_only_its_line(client):
    provider, survey = create_survey([({"snap_gender": "FEMALE"}, PENDING)] * 5)

    content = get_dashboard(client, provider, survey, group_by="gender")

    assert NOT_ANALYSED in content
    assert "of 5 answers.</p>" not in content
    assert 'class="sentiment-bar"' not in content
    assert "By gender" not in content
    assert NOT_ENOUGH not in content
    assert '<option value="gender" selected>Gender</option>' in content


@pytest.mark.django_db
def test_age_breakdown_uses_the_age_group_heading(client):
    entries = [({"snap_age": 30}, POSITIVE)] * 5 + [({"snap_age": 60}, NEGATIVE)] * 5
    provider, survey = create_survey(entries)

    content = get_dashboard(client, provider, survey, group_by="age")

    assert "By age group</h4>" in content
    rows = re.findall(r'<th scope="row">([^<]*)</th>', content)
    assert rows == ["25 to 34", "55 and over"]


@pytest.mark.django_db
def test_unknown_group_by_shows_no_breakdown_selected(client):
    provider, survey = create_survey([({}, POSITIVE)] * 5)

    content = get_dashboard(client, provider, survey, group_by="email")

    assert '<option value="" selected>No breakdown</option>' in content
    assert "group-breakdown-table" not in content
