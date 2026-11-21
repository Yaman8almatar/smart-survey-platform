"""FR-13: one filter by gender, age group or governorate, and responses over time (TASK-56).

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5).
"""

import datetime
from itertools import count

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

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
        email=f"fr13-filter-{next(_emails)}@example.com",
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


def add_response(survey, excluded=False, **snapshot):
    respondent = create_user(UserType.RESPONDENT)
    return ResponseRepository().save(
        Response(survey=survey, respondent=respondent, is_excluded=excluded, **snapshot)
    )


def answer(response, question, **values):
    return ResponseRepository().save_answer(Answer(response=response, question=question, **values))


def analysed(answer_row, label=SentimentLabel.POSITIVE):
    return SentimentAnalysisResult.objects.create(
        answer=answer_row, status=AnalysisStatus.COMPLETED, sentiment_label=label
    )


def results(provider, survey, **kwargs):
    return AnalysisService(analyzer=FakeClient()).get_survey_results(
        provider, survey.survey_id, **kwargs
    )


def summary_of(result, question):
    return next(
        summary
        for summary in result["question_summaries"]
        if summary["question_id"] == question.question_id
    )


def build_gender_survey():
    """20 included responses (Male 10, Female 6, not stated 4) and 2 excluded not stated.

    Governorates: Damascus 8, Aleppo 5, Homs 4, Hama 3; no age. Each response answers
    the choice question (Male: Yes; others: No, except two Female Yes) and the rating
    (Male 5, Female 3, not stated 1).
    """
    provider, survey = create_survey()
    choice, (yes, no) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Yes", "No"), 0)
    rating, _ = add_question(survey, QuestionType.RATING_SCALE, order=1)
    genders = ["MALE"] * 10 + ["FEMALE"] * 6 + [""] * 4
    regions = ["DAMASCUS"] * 8 + ["ALEPPO"] * 5 + ["HOMS"] * 4 + ["HAMA"] * 3
    for index, (gender, region) in enumerate(zip(genders, regions)):
        response = add_response(survey, snap_gender=gender, snap_region=region)
        picked = yes if gender == "MALE" or (gender == "FEMALE" and index < 12) else no
        answer(response, choice, selected_option=picked)
        answer(response, rating, rating_value={"MALE": 5, "FEMALE": 3, "": 1}[gender])
    for _ in range(2):
        excluded = add_response(survey, excluded=True, snap_gender="", snap_region="DAMASCUS")
        answer(excluded, choice, selected_option=yes)
    return provider, survey, choice, rating


def test_group_key_is_the_stable_twin_of_the_label():
    service = AnalysisService(analyzer=FakeClient())
    ages = {
        None: "not-stated",
        17: "under-18",
        18: "18-24",
        24: "18-24",
        25: "25-34",
        44: "35-44",
        54: "45-54",
        55: "55-plus",
    }
    for age, key in ages.items():
        assert service._group_key(Response(snap_age=age), "age") == key
    assert service._group_key(Response(snap_gender="MALE"), "gender") == "MALE"
    assert service._group_key(Response(snap_gender="ANY"), "gender") == "not-stated"
    assert service._group_key(Response(snap_gender=""), "gender") == "not-stated"
    assert service._group_key(Response(snap_region="HOMS"), "governorate") == "HOMS"
    assert service._group_key(Response(snap_region="Nowhere"), "governorate") == "not-stated"


@pytest.mark.django_db
def test_filter_options_pool_small_groups_and_skip_a_dimension_with_one_row():
    provider, survey, _choice, _rating = build_gender_survey()

    result = results(provider, survey)

    # Gender: the pool of 4 not stated pulls Female in. Age: one row, nothing offered.
    # Governorate: Homs 4 and Hama 3 are pooled. The 2 excluded responses are not counted,
    # or "not stated" would have 6 and be offered on its own.
    assert result["filter_options"] == [
        {"key": "gender:MALE", "label": "Gender: Male"},
        {"key": "gender:other", "label": "Gender: Other groups (combined)"},
        {"key": "governorate:DAMASCUS", "label": "Governorate: Damascus"},
        {"key": "governorate:ALEPPO", "label": "Governorate: Aleppo"},
        {"key": "governorate:other", "label": "Governorate: Other groups (combined)"},
    ]
    assert result["filter"] is None
    assert result["filter_unavailable"] is False
    assert all(summary["too_few"] is False for summary in result["question_summaries"])


@pytest.mark.django_db
def test_offered_filter_shows_the_hand_counted_figures_of_the_group():
    provider, survey, choice, rating = build_gender_survey()

    result = results(provider, survey, filter_key="gender:MALE")

    assert result["filter"] == {"key": "gender:MALE", "label": "Gender: Male", "count": 10}
    assert result["filter_unavailable"] is False
    choice_summary = summary_of(result, choice)
    assert choice_summary["too_few"] is False
    assert choice_summary["labels"] == ["Yes", "No"]
    assert choice_summary["values"] == [10, 0]
    assert summary_of(result, rating)["values"] == [0, 0, 0, 0, 10]


@pytest.mark.django_db
def test_other_filter_covers_the_pooled_groups():
    provider, survey, choice, rating = build_gender_survey()

    result = results(provider, survey, filter_key="gender:other")

    assert result["filter"] == {
        "key": "gender:other",
        "label": "Gender: Other groups (combined)",
        "count": 10,
    }
    # Female 6 (2 Yes, 4 No) and not stated 4 (No).
    assert summary_of(result, choice)["values"] == [2, 8]
    assert summary_of(result, rating)["values"] == [4, 0, 6, 0, 0]


@pytest.mark.django_db
@pytest.mark.parametrize("key", ["gender:FEMALE", "age:not-stated", "colour:red", "gender"])
def test_a_filter_that_is_not_offered_is_unavailable(key):
    provider, survey, choice, _rating = build_gender_survey()

    result = results(provider, survey, filter_key=key)

    assert result["filter"] is None
    assert result["filter_unavailable"] is True
    assert summary_of(result, choice)["values"] == [12, 8]


@pytest.mark.django_db
def test_empty_filter_key_is_no_filter():
    provider, survey, _choice, _rating = build_gender_survey()

    result = results(provider, survey, filter_key="")

    assert result["filter"] is None
    assert result["filter_unavailable"] is False


@pytest.mark.django_db
def test_question_answered_by_four_of_the_group_is_too_few():
    provider, survey, _choice, _rating = build_gender_survey()
    optional, (only,) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Only",), 2)
    males = Response.objects.filter(survey=survey, snap_gender="MALE").order_by("response_id")
    for response in males[:4]:
        answer(response, optional, selected_option=only)

    result = results(provider, survey, filter_key="gender:MALE")

    summary = summary_of(result, optional)
    assert summary["too_few"] is True
    assert summary["labels"] == []
    assert summary["values"] == []


@pytest.mark.django_db
def test_no_difference_of_two_filters_gives_two_answers():
    """Male 20, Female 10, not stated 2 on an optional question: rows Male and the pool."""
    provider, survey = create_survey()
    optional, (agree,) = add_question(survey, QuestionType.MULTIPLE_CHOICE, ("Agree",), 0)
    for gender, total, answering in (("MALE", 20, 20), ("FEMALE", 10, 10), ("", 5, 2)):
        for index in range(total):
            response = add_response(survey, snap_gender=gender)
            if index < answering:
                answer(response, optional, selected_option=agree)

    whole = results(provider, survey)
    male = results(provider, survey, filter_key="gender:MALE")
    female = results(provider, survey, filter_key="gender:FEMALE")
    not_stated = results(provider, survey, filter_key="gender:not-stated")

    assert [option["key"] for option in whole["filter_options"]][:3] == [
        "gender:MALE",
        "gender:FEMALE",
        "gender:not-stated",
    ]
    assert summary_of(whole, optional)["values"] == [32]
    assert summary_of(male, optional)["values"] == [20]
    assert summary_of(female, optional)["too_few"] is True
    assert summary_of(not_stated, optional)["too_few"] is True


def build_open_survey(male_analysed):
    """Male 10, Female 6, not stated 4, each with an open answer; Female 6 analysed."""
    provider, survey = create_survey()
    question, _ = add_question(survey, QuestionType.OPEN_TEXT, order=0)
    analysed_males = 0
    for gender, total in (("MALE", 10), ("FEMALE", 6), ("", 4)):
        for index in range(total):
            response = add_response(survey, snap_gender=gender, snap_region="DAMASCUS")
            row = answer(response, question, answer_value=f"{gender or 'none'} answer {index}")
            if gender == "FEMALE":
                analysed(row, SentimentLabel.NEGATIVE)
            elif gender == "MALE" and analysed_males < male_analysed:
                analysed(row, SentimentLabel.POSITIVE)
                analysed_males += 1
    return provider, survey, question


@pytest.mark.django_db
def test_open_question_under_a_filter_with_four_analysed_shows_nothing():
    provider, survey, question = build_open_survey(male_analysed=4)

    summary = summary_of(results(provider, survey, filter_key="gender:MALE"), question)

    assert summary["too_few"] is True
    assert summary["text_hidden"] is True
    assert summary["text_answers"] == []
    assert summary["text_answer_total"] == 0
    assert summary["sentiment"] == {
        "total": 0,
        "analysed": 0,
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }


@pytest.mark.django_db
def test_open_question_under_a_filter_with_five_analysed_shows_the_group_sentiment():
    provider, survey, question = build_open_survey(male_analysed=5)

    filtered = summary_of(results(provider, survey, filter_key="gender:MALE"), question)
    whole = summary_of(results(provider, survey), question)

    assert filtered["too_few"] is False
    assert filtered["text_hidden"] is True
    assert filtered["text_answers"] == []
    assert filtered["text_answer_total"] == 0
    assert filtered["sentiment"] == {
        "total": 5,
        "analysed": 5,
        "positive": 5,
        "neutral": 0,
        "negative": 0,
    }
    assert whole["text_hidden"] is False
    assert whole["text_answer_total"] == 20


@pytest.mark.django_db
def test_group_by_is_ignored_with_a_filter():
    provider, survey, choice, _rating = build_gender_survey()

    result = results(provider, survey, group_by="governorate", filter_key="gender:MALE")

    assert result["group_by"] is None
    assert "group_table" not in summary_of(result, choice)


@pytest.mark.django_db
def test_top_counts_stay_whole_survey_under_a_filter():
    provider, survey, _choice, _rating = build_gender_survey()
    whole = results(provider, survey)

    filtered = results(provider, survey, filter_key="gender:MALE")

    for key in (
        "response_count",
        "included_count",
        "positive_count",
        "neutral_count",
        "negative_count",
        "positive_rate",
        "filter_options",
        "responses_over_time",
    ):
        assert filtered[key] == whole[key]
    assert filtered["response_count"] == 22
    assert filtered["included_count"] == 20


@pytest.mark.django_db
def test_responses_over_time_counts_excluded_responses_and_fills_zero_days():
    provider, survey = create_survey()
    days = [
        (datetime.date(2026, 11, 18), False),
        (datetime.date(2026, 11, 18), False),
        (datetime.date(2026, 11, 20), False),
        (datetime.date(2026, 11, 20), True),
        (datetime.date(2026, 11, 21), False),
    ]
    for day, excluded in days:
        response = add_response(survey, excluded=excluded)
        Response.objects.filter(pk=response.pk).update(
            submitted_at=datetime.datetime.combine(
                day, datetime.time(23, 30), tzinfo=datetime.timezone.utc
            )
        )

    result = results(provider, survey)

    assert result["responses_over_time"] == [
        {"date": datetime.date(2026, 11, 18), "count": 2},
        {"date": datetime.date(2026, 11, 19), "count": 0},
        {"date": datetime.date(2026, 11, 20), "count": 2},
        {"date": datetime.date(2026, 11, 21), "count": 1},
    ]


@pytest.mark.django_db
def test_responses_over_time_is_empty_without_a_response(monkeypatch):
    monkeypatch.setattr("services.disclosure.MIN_GROUP_SIZE", 0)
    provider, survey = create_survey()

    assert results(provider, survey)["responses_over_time"] == []


@pytest.mark.django_db
def test_locked_result_is_unchanged_with_a_filter(django_assert_max_num_queries):
    provider, survey = create_survey()
    for _ in range(4):
        add_response(survey, snap_gender="MALE")
    service = AnalysisService(analyzer=FakeClient())

    with django_assert_max_num_queries(2):
        result = service.get_survey_results(
            provider, survey.survey_id, group_by="gender", filter_key="gender:MALE"
        )

    assert result == {
        "survey_id": survey.survey_id,
        "response_count": 4,
        "locked": True,
        "min_responses": 5,
    }


def count_queries(provider, survey, **kwargs):
    with CaptureQueriesContext(connection) as captured:
        results(provider, survey, **kwargs)
    return len(captured.captured_queries)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kwargs", [{}, {"filter_key": "gender:MALE"}, {"group_by": "governorate"}]
)
def test_query_count_does_not_grow_with_the_responses(kwargs):
    provider, survey, choice, rating = build_gender_survey()
    before = count_queries(provider, survey, **kwargs)
    yes = QuestionOption.objects.filter(question=choice).first()
    for _ in range(10):
        response = add_response(survey, snap_gender="MALE", snap_region="DAMASCUS")
        answer(response, choice, selected_option=yes)
        answer(response, rating, rating_value=4)

    assert count_queries(provider, survey, **kwargs) == before
