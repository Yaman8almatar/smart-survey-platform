"""FR-13 on the analytics page: the filter card, comparison tables, responses over time (TASK-56).

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5).
"""

import datetime
import json
import re
from itertools import count

import pytest
from django.urls import reverse

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    Response,
    SentimentAnalysisResult,
    Survey,
    User,
)
from core.enums import AccountStatus, AnalysisStatus, QuestionType, SentimentLabel, UserType
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository

CARD_TITLE = '<h2 class="section-title">Filter results</h2>'
HELPER = (
    "Show the question results for one group. Groups come from each respondent's profile "
    "when they answered; groups with fewer than 5 responses are combined."
)
TOO_FEW = "Not enough answers to show this question for this group."
OPEN_HIDDEN = "Open answers are not listed while a filter is on."
UNAVAILABLE = "This filter is not available. Showing all respondents."
COMPARISON_OFF = "Comparison is off while a filter is on."
CHOICE_CAPTION = "Shares of the answers in each group."
OVER_TIME_TITLE = "Responses over time"
OVER_TIME_CAPTION = "All submitted responses, by day (UTC)."
NOT_ENOUGH = "Not enough responses to show this breakdown."

_emails = count()


def create_user(user_type):
    return User.objects.create_user(
        email=f"fr13-view-{next(_emails)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def add_question(survey, question_type, options=(), order=0, text=None):
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text=text or f"Question {order}?",
            question_type=question_type,
            is_required=False,
            order_index=order,
        )
    )
    created = [
        QuestionOption.objects.create(question=question, option_text=option, order_index=index)
        for index, option in enumerate(options)
    ]
    return question, created


def create_survey(responses=True):
    """Male 10, Female 6, not stated 4; Damascus 6, Aleppo 5, Homs 5, Hama 4.

    Questions: a choice (Yes/No), a rating, an open question with every Female answer
    analysed, and an optional choice answered by 4 Male respondents only.
    """
    provider = create_user(UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    choice, (yes, no) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Yes", "No"), 0)
    rating, _ = add_question(survey, QuestionType.RATING_SCALE, order=1)
    open_question, _ = add_question(survey, QuestionType.OPEN_TEXT, order=2)
    optional, (only,) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Only",), 3)
    if not responses:
        return provider, survey
    genders = ["MALE"] * 10 + ["FEMALE"] * 6 + [""] * 4
    regions = ["DAMASCUS"] * 6 + ["ALEPPO"] * 5 + ["HOMS"] * 5 + ["HAMA"] * 4
    for index, (gender, region) in enumerate(zip(genders, regions)):
        response = ResponseRepository().save(
            Response(
                survey=survey,
                respondent=create_user(UserType.RESPONDENT),
                snap_gender=gender,
                snap_region=region,
            )
        )
        save = ResponseRepository().save_answer
        save(Answer(response=response, question=choice, selected_option=yes if gender == "MALE" else no))
        save(Answer(response=response, question=rating, rating_value=4))
        text = save(Answer(response=response, question=open_question, answer_value=f"Text {index}"))
        if gender == "FEMALE":
            SentimentAnalysisResult.objects.create(
                answer=text, status=AnalysisStatus.COMPLETED, sentiment_label=SentimentLabel.POSITIVE
            )
        if gender == "MALE" and index < 4:
            save(Answer(response=response, question=optional, selected_option=only))
    return provider, survey


def get_dashboard(client, provider, survey, **params):
    client.force_login(provider)
    url = reverse("analysis:analytics_dashboard", args=[survey.survey_id])
    return client.get(url, params).content.decode()


@pytest.mark.django_db
def test_filter_card_sits_above_question_results_with_its_options_in_order(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey)

    assert CARD_TITLE in content
    assert HELPER in content
    assert content.index(CARD_TITLE) < content.index("Question results</h2>")
    assert content.index("Group breakdown</h2>") < content.index(CARD_TITLE)
    assert '<label class="form-label" for="filter-select">Show results for</label>' in content
    assert '<select class="form-select" id="filter-select" name="filter">' in content
    form = content.split('id="filter-select"', 1)[1].split("</form>", 1)[0]
    assert re.findall(r'name="([^"]+)"', form) == ["filter"]  # the form's only field
    options = re.findall(r'<option label="([^"]*)" value="([^"]*)"( selected)?>([^<]*)</option>', form)
    assert options == [
        ("All respondents", "", "", "All respondents"),
        ("Gender: Male", "gender:MALE", "", "Gender: Male"),
        ("Gender: Other groups (combined)", "gender:other", "", "Gender: Other groups (combined)"),
        ("Governorate: Damascus", "governorate:DAMASCUS", "", "Governorate: Damascus"),
        ("Governorate: Aleppo", "governorate:ALEPPO", "", "Governorate: Aleppo"),
        # Hama's 4 pull Homs in: of Aleppo 5 and Homs 5, the one listed last.
        (
            "Governorate: Other groups (combined)",
            "governorate:other",
            "",
            "Governorate: Other groups (combined)",
        ),
    ]
    assert '<button type="submit" class="btn btn-outline-secondary">Show</button>' in form
    assert "Showing " not in content
    assert COMPARISON_OFF not in content
    assert OPEN_HIDDEN not in content


@pytest.mark.django_db
def test_filter_on_shows_the_filtered_line_and_notes(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey, filter="gender:MALE")

    assert '<option label="Gender: Male" value="gender:MALE" selected>Gender: Male</option>' in content
    assert "Showing 10 of 20 included responses: Gender: Male." in content
    question_results = content.split("Question results</h2>", 1)[1]
    # The optional question has 4 Male answers; the open question has none analysed.
    assert question_results.count(TOO_FEW) == 2
    assert OPEN_HIDDEN in question_results
    assert "Text 0" not in content
    assert COMPARISON_OFF in content
    assert content.index("Group breakdown</h2>") < content.index(COMPARISON_OFF)
    assert content.index(COMPARISON_OFF) < content.index('for="group-by-select"')
    assert UNAVAILABLE not in content


@pytest.mark.django_db
def test_too_few_question_has_no_chart_data(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey, filter="gender:MALE")

    chart_data = json.loads(
        re.search(r'<script id="question-chart-data" type="application/json">(.*?)</script>', content).group(1)
    )
    assert [payload["values"] for payload in chart_data] == [[10, 0], [0, 0, 0, 10, 0]]


@pytest.mark.django_db
def test_unavailable_filter_shows_the_note_and_all_respondents(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey, filter="gender:FEMALE")

    assert UNAVAILABLE in content
    assert "included responses:" not in content
    assert TOO_FEW not in content
    assert "Text 0" in content


@pytest.mark.django_db
def test_choice_and_rating_tables_under_group_by(client):
    provider, survey = create_survey()

    content = get_dashboard(client, provider, survey, group_by="gender")

    question_results = content.split("Question results</h2>", 1)[1]
    tables = re.findall(r'<table class="table group-breakdown-table">(.*?)</table>', question_results, re.S)
    choice_table, rating_table = tables[0], tables[1]
    assert re.findall(r'<th scope="col">([^<]*)</th>', choice_table) == ["Group", "Answers", "Yes", "No"]
    assert re.findall(r'<th scope="row">([^<]*)</th>\s*<td>(\d+)</td>', choice_table) == [
        ("Male", "10"),
        ("Other groups (combined)", "10"),
    ]
    assert '10 <span class="group-breakdown-table__share">100%</span>' in choice_table
    assert 'class="group-breakdown-table__pooled"' in choice_table
    assert re.findall(r'<th scope="col">([^<]*)</th>', rating_table) == ["Group", "Answers", "Average"]
    assert re.findall(r'<th scope="row">([^<]*)</th>\s*<td>(\d+)</td>\s*<td>([^<]*)</td>', rating_table) == [
        ("Male", "10", "4.0"),
        ("Other groups (combined)", "10", "4.0"),
    ]
    assert question_results.count("By gender</h4>") == 4  # two tables, the open breakdown, the optional
    assert question_results.count(CHOICE_CAPTION) == 1
    # The optional question has 4 answers, one row: no table.
    assert NOT_ENOUGH in question_results


@pytest.mark.django_db
def test_responses_over_time_card_with_its_chart_data_and_caption(client):
    provider, survey = create_survey()
    Response.objects.filter(survey=survey).update(
        submitted_at=datetime.datetime(2026, 11, 19, 10, tzinfo=datetime.timezone.utc)
    )
    first = Response.objects.filter(survey=survey).order_by("response_id").first()
    Response.objects.filter(pk=first.pk).update(
        submitted_at=datetime.datetime(2026, 11, 21, 10, tzinfo=datetime.timezone.utc)
    )

    content = get_dashboard(client, provider, survey)

    assert f'<h2 class="section-title mb-3">{OVER_TIME_TITLE}</h2>' in content
    data = json.loads(
        re.search(
            r'<script id="responses-over-time-data" type="application/json">(.*?)</script>', content
        ).group(1)
    )
    assert data == [
        {"label": "19 Nov", "count": 19},
        {"label": "20 Nov", "count": 0},
        {"label": "21 Nov", "count": 1},
    ]
    assert (
        '<canvas id="surveyResponsesOverTimeChart" aria-label="Submitted responses per day" role="img">'
        in content
    )
    assert OVER_TIME_CAPTION in content
    assert content.index("Group breakdown</h2>") < content.index(OVER_TIME_TITLE)
    assert content.index(OVER_TIME_TITLE) < content.index(CARD_TITLE)


@pytest.mark.django_db
def test_no_over_time_card_without_a_response(client, monkeypatch):
    monkeypatch.setattr("services.disclosure.MIN_GROUP_SIZE", 0)
    provider, survey = create_survey(responses=False)

    content = get_dashboard(client, provider, survey)

    assert OVER_TIME_TITLE not in content
    assert "responses-over-time-data" not in content


@pytest.mark.django_db
def test_locked_survey_shows_none_of_it(client):
    provider, survey = create_survey(responses=False)
    for _ in range(4):
        ResponseRepository().save(
            Response(survey=survey, respondent=create_user(UserType.RESPONDENT), snap_gender="MALE")
        )

    content = get_dashboard(client, provider, survey, filter="gender:MALE", group_by="gender")

    for text in (CARD_TITLE, OVER_TIME_TITLE, "responses-over-time-data", "included responses:", UNAVAILABLE, COMPARISON_OFF):
        assert text not in content
