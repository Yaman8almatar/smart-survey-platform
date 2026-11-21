"""FR-13: comparison tables of multiple-choice and rating questions by group (TASK-56).

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5).
"""

from itertools import count

import pytest

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
from services.analysis_service import AnalysisService

_emails = count()


class FakeClient:
    model_id = "org/sentiment-model"

    def analyze_sentiment(self, text):
        raise AssertionError("Reading results must not call the analysis client.")


def create_user(user_type):
    return User.objects.create_user(
        email=f"fr13-table-{next(_emails)}@example.com",
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey():
    provider = create_user(UserType.SERVICE_PROVIDER)
    survey = SurveyRepository().save(
        Survey(provider=provider, title="Survey", description="Description")
    )
    return provider, survey


def add_question(survey, question_type, options=(), order=0):
    question = QuestionRepository().save(
        Question(
            survey=survey,
            question_text=f"Question {order}?",
            question_type=question_type,
            is_required=False,
            order_index=order,
        )
    )
    created = [
        QuestionOption.objects.create(question=question, option_text=text, order_index=index)
        for index, text in enumerate(options)
    ]
    return question, created


def add_response(survey, **snapshot):
    return ResponseRepository().save(
        Response(survey=survey, respondent=create_user(UserType.RESPONDENT), **snapshot)
    )


def answer(response, question, **values):
    return ResponseRepository().save_answer(Answer(response=response, question=question, **values))


def summary_of(provider, survey, question, **kwargs):
    result = AnalysisService(analyzer=FakeClient()).get_survey_results(
        provider, survey.survey_id, **kwargs
    )
    return next(
        summary
        for summary in result["question_summaries"]
        if summary["question_id"] == question.question_id
    )


def build_region_survey():
    """Damascus 6, Aleppo 5, Homs 3, Hama 2; one choice and one rating question."""
    provider, survey = create_survey()
    choice, (red, green, blue) = add_question(
        survey, QuestionType.MULTIPLE_CHOICE, ("Red", "Green", "Blue"), 0
    )
    rating, _ = add_question(survey, QuestionType.RATING_SCALE, order=1)
    rows = (
        [("DAMASCUS", red, 5)] * 3
        + [("DAMASCUS", blue, 4)] * 2
        + [("DAMASCUS", blue, 3)]
        + [("ALEPPO", green, rating_value) for rating_value in (1, 2, 3, 4, 5)]
        + [("HOMS", red, 2)] * 2
        + [("HOMS", green, 2)]
        + [("HAMA", blue, 1)] * 2
    )
    for region, option, rating_value in rows:
        response = add_response(survey, snap_region=region)
        answer(response, choice, selected_option=option)
        answer(response, rating, rating_value=rating_value)
    return provider, survey, choice, rating


@pytest.mark.django_db
def test_choice_table_has_counts_and_shares_in_option_order():
    provider, survey, choice, _rating = build_region_survey()

    summary = summary_of(provider, survey, choice, group_by="governorate")

    assert summary["group_table"] == {
        "dimension": "governorate",
        "enough": True,
        "rows": [
            {
                "label": "Damascus",
                "answers": 6,
                "shares": [
                    {"option": "Red", "count": 3, "share": 0.5},
                    {"option": "Green", "count": 0, "share": 0.0},
                    {"option": "Blue", "count": 3, "share": 0.5},
                ],
                "pooled": False,
            },
            {
                "label": "Aleppo",
                "answers": 5,
                "shares": [
                    {"option": "Red", "count": 0, "share": 0.0},
                    {"option": "Green", "count": 5, "share": 1.0},
                    {"option": "Blue", "count": 0, "share": 0.0},
                ],
                "pooled": False,
            },
            {
                "label": "Other groups (combined)",
                "answers": 5,
                "shares": [
                    {"option": "Red", "count": 2, "share": 0.4},
                    {"option": "Green", "count": 1, "share": 0.2},
                    {"option": "Blue", "count": 2, "share": 0.4},
                ],
                "pooled": True,
            },
        ],
    }
    # The whole-survey chart is unchanged by the table.
    assert summary["values"] == [5, 6, 5]


@pytest.mark.django_db
def test_rating_table_has_answers_and_average():
    provider, survey, _choice, rating = build_region_survey()

    summary = summary_of(provider, survey, rating, group_by="governorate")

    assert summary["group_table"] == {
        "dimension": "governorate",
        "enough": True,
        "rows": [
            {"label": "Damascus", "answers": 6, "average": 4.33, "pooled": False},
            {"label": "Aleppo", "answers": 5, "average": 3.0, "pooled": False},
            {"label": "Other groups (combined)", "answers": 5, "average": 1.6, "pooled": True},
        ],
    }


@pytest.mark.django_db
def test_table_pools_on_the_question_own_answerers():
    """Responses: Damascus 7, Aleppo 6, Homs 6; the optional question: 7, 6 and 3."""
    provider, survey = create_survey()
    optional, (only,) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Only",), 0)
    for region, total, answering in (("DAMASCUS", 7, 7), ("ALEPPO", 6, 6), ("HOMS", 6, 3)):
        for index in range(total):
            response = add_response(survey, snap_region=region)
            if index < answering:
                answer(response, optional, selected_option=only)

    table = summary_of(provider, survey, optional, group_by="governorate")["group_table"]

    # Homs' 3 answerers pull Aleppo, the smallest shown group, into the pool.
    assert [(row["label"], row["answers"], row["pooled"]) for row in table["rows"]] == [
        ("Damascus", 7, False),
        ("Other groups (combined)", 9, True),
    ]


@pytest.mark.django_db
def test_table_with_fewer_than_two_rows_has_no_row():
    provider, survey = create_survey()
    rating, _ = add_question(survey, QuestionType.RATING_SCALE, order=0)
    for region, total in (("DAMASCUS", 6), ("ALEPPO", 3)):
        for _ in range(total):
            answer(add_response(survey, snap_region=region), rating, rating_value=4)

    summary = summary_of(provider, survey, rating, group_by="governorate")

    assert summary["group_table"] == {"dimension": "governorate", "enough": False, "rows": []}


@pytest.mark.django_db
def test_no_table_without_group_by():
    provider, survey, choice, rating = build_region_survey()

    assert "group_table" not in summary_of(provider, survey, choice)
    assert "group_table" not in summary_of(provider, survey, rating)


@pytest.mark.django_db
def test_open_question_keeps_its_breakdown_and_gets_no_table():
    provider, survey = create_survey()
    question, _ = add_question(survey, QuestionType.OPEN_TEXT, order=0)
    for gender, label in (("MALE", SentimentLabel.POSITIVE), ("FEMALE", SentimentLabel.NEGATIVE)):
        for index in range(5):
            row = answer(add_response(survey, snap_gender=gender), question, answer_value="Fine")
            SentimentAnalysisResult.objects.create(
                answer=row, status=AnalysisStatus.COMPLETED, sentiment_label=label
            )

    summary = summary_of(provider, survey, question, group_by="gender")

    assert "group_table" not in summary
    assert summary["breakdown"] == {
        "dimension": "gender",
        "enough": True,
        "rows": [
            {
                "label": "Female",
                "analysed": 5,
                "positive": 0,
                "neutral": 0,
                "negative": 5,
                "pooled": False,
            },
            {
                "label": "Male",
                "analysed": 5,
                "positive": 5,
                "neutral": 0,
                "negative": 0,
                "pooled": False,
            },
        ],
    }
