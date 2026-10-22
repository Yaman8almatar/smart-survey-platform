import pytest
import requests
from django.utils import timezone

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    Response,
    SentimentAnalysisResult,
    Survey,
    User,
)
from core.enums import (
    AccountStatus,
    AnalysisStatus,
    QuestionType,
    SentimentLabel,
    UserType,
)
from core.exceptions import ExternalAnalysisServiceError
from infrastructure.huggingface_client import HuggingFaceClient
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services.analysis_service import AnalysisService


class FakeHuggingFaceClient:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [{"label": "positive", "score": 0.9}])
        self.error = error
        self.calls = []

    def analyze_sentiment(self, text):
        self.calls.append(text)
        if self.error:
            raise self.error
        return self.responses.pop(0)


class FakeHuggingFaceResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


@pytest.fixture
def analysis_repository():
    return AnalysisRepository()


def create_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def create_survey(provider, title="Survey"):
    return SurveyRepository().save(
        Survey(provider=provider, title=title, description="Description")
    )


def create_question(survey, question_type, text="Question?"):
    return QuestionRepository().save(
        Question(
            survey=survey,
            question_text=text,
            question_type=question_type,
            is_required=True,
            order_index=0,
        )
    )


def create_response(survey, respondent):
    return ResponseRepository().save(Response(survey=survey, respondent=respondent))


def create_answer(response, question, **values):
    return ResponseRepository().save_answer(
        Answer(response=response, question=question, **values)
    )


def create_sentiment_result(answer, label, status=AnalysisStatus.COMPLETED):
    return AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=status,
            sentiment_label=label,
            sentiment_score=0.9,
            analyzed_at=timezone.now(),
        )
    )


def create_survey_response():
    provider = create_user("provider-analysis@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-analysis@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    response = create_response(survey, respondent)
    return survey, response


def mock_hugging_face_response(monkeypatch, payload):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeHuggingFaceResponse(payload)

    monkeypatch.setenv("HF_API_TOKEN", "test-token")
    monkeypatch.setenv("HF_SENTIMENT_MODEL_URL", "https://example.com/model")
    monkeypatch.setattr("infrastructure.huggingface_client.requests.post", fake_post)
    return calls


def fail_if_hugging_face_is_called(*args, **kwargs):
    raise AssertionError("The real Hugging Face API must not be called in tests.")


@pytest.mark.django_db
def test_analyze_open_text_answers_analyzes_only_open_text_answers():
    survey, response = create_survey_response()
    open_question = create_question(survey, QuestionType.OPEN_TEXT)
    choice_question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    rating_question = create_question(survey, QuestionType.RATING_SCALE)
    option = QuestionRepository().save_option(
        QuestionOption(question=choice_question, option_text="Good", order_index=0)
    )
    create_answer(response, open_question, answer_value="Great service")
    create_answer(response, choice_question, selected_option=option)
    create_answer(response, rating_question, rating_value=5)
    fake_client = FakeHuggingFaceClient()
    service = AnalysisService(huggingface_client=fake_client)

    results = service.analyze_open_text_answers(response.response_id)

    assert len(results) == 1
    assert fake_client.calls == ["Great service"]


@pytest.mark.django_db
def test_multiple_choice_answers_are_not_sent_to_huggingface_client():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    option = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="Good", order_index=0)
    )
    create_answer(response, question, selected_option=option)
    fake_client = FakeHuggingFaceClient()
    service = AnalysisService(huggingface_client=fake_client)

    results = service.analyze_open_text_answers(response.response_id)

    assert results == []
    assert fake_client.calls == []


@pytest.mark.django_db
def test_rating_scale_answers_are_not_sent_to_huggingface_client():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.RATING_SCALE)
    create_answer(response, question, rating_value=4)
    fake_client = FakeHuggingFaceClient()
    service = AnalysisService(huggingface_client=fake_client)

    results = service.analyze_open_text_answers(response.response_id)

    assert results == []
    assert fake_client.calls == []


@pytest.mark.django_db
def test_successful_external_analysis_creates_completed_result(analysis_repository):
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Great service")
    fake_client = FakeHuggingFaceClient(
        responses=[{"label": "positive", "score": 0.95}]
    )
    service = AnalysisService(huggingface_client=fake_client)

    service.analyze_open_text_answers(response.response_id)

    result = analysis_repository.find_by_answer_id(answer.answer_id)
    assert result.status == AnalysisStatus.COMPLETED
    assert result.sentiment_label == SentimentLabel.POSITIVE
    assert result.sentiment_score == 0.95
    assert result.analyzed_at is not None


@pytest.mark.django_db
def test_failed_external_analysis_creates_failed_result(analysis_repository):
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Great service")
    fake_client = FakeHuggingFaceClient(
        error=ExternalAnalysisServiceError("External service failed.")
    )
    service = AnalysisService(huggingface_client=fake_client)

    service.analyze_open_text_answers(response.response_id)

    result = analysis_repository.find_by_answer_id(answer.answer_id)
    assert result.status == AnalysisStatus.FAILED
    assert result.sentiment_label is None
    assert result.sentiment_score is None


@pytest.mark.django_db
def test_analysis_service_maps_normalized_client_result_to_sentiment_label(
    analysis_repository,
):
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Bad service")
    fake_client = FakeHuggingFaceClient(
        responses=[{"label": "NEGATIVE", "score": 0.88}]
    )
    service = AnalysisService(huggingface_client=fake_client)

    service.analyze_open_text_answers(response.response_id)

    result = analysis_repository.find_by_answer_id(answer.answer_id)
    assert result.status == AnalysisStatus.COMPLETED
    assert result.sentiment_label == SentimentLabel.NEGATIVE
    assert result.sentiment_score == 0.88


def test_single_label_hugging_face_response_is_normalized(monkeypatch):
    calls = mock_hugging_face_response(
        monkeypatch,
        [{"label": "Positive", "score": 0.95}],
    )
    client = HuggingFaceClient()

    result = client.analyze_sentiment("Great service")

    assert result == {"label": "POSITIVE", "score": 0.95}
    assert calls == [
        {
            "url": "https://example.com/model",
            "headers": {"Authorization": "Bearer test-token"},
            "json": {"inputs": "Great service"},
            "timeout": 15,
        }
    ]


def test_nested_multi_label_hugging_face_response_uses_highest_score(monkeypatch):
    calls = mock_hugging_face_response(
        monkeypatch,
        [[
            {"label": "Negative", "score": 0.1},
            {"label": "Neutral", "score": 0.2},
            {"label": "Positive", "score": 0.7},
        ]],
    )
    client = HuggingFaceClient()

    result = client.analyze_sentiment("Great service")

    assert result == {"label": "POSITIVE", "score": 0.7}
    assert len(calls) == 1


def test_label_0_maps_to_negative(monkeypatch):
    mock_hugging_face_response(monkeypatch, [{"label": "LABEL_0", "score": 0.6}])
    client = HuggingFaceClient()

    result = client.analyze_sentiment("Poor service")

    assert result == {"label": "NEGATIVE", "score": 0.6}


def test_label_1_maps_to_neutral(monkeypatch):
    mock_hugging_face_response(monkeypatch, [{"label": "LABEL_1", "score": 0.6}])
    client = HuggingFaceClient()

    result = client.analyze_sentiment("Average service")

    assert result == {"label": "NEUTRAL", "score": 0.6}


def test_label_2_maps_to_positive(monkeypatch):
    mock_hugging_face_response(monkeypatch, [{"label": "LABEL_2", "score": 0.6}])
    client = HuggingFaceClient()

    result = client.analyze_sentiment("Great service")

    assert result == {"label": "POSITIVE", "score": 0.6}


def test_unknown_hugging_face_label_raises_external_analysis_service_error(
    monkeypatch,
):
    mock_hugging_face_response(monkeypatch, [{"label": "MIXED", "score": 0.6}])
    client = HuggingFaceClient()

    with pytest.raises(ExternalAnalysisServiceError):
        client.analyze_sentiment("Mixed service")


def test_missing_hugging_face_token_raises_external_analysis_service_error(monkeypatch):
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.setenv("HF_SENTIMENT_MODEL_URL", "https://example.com/model")
    monkeypatch.setattr(
        "infrastructure.huggingface_client.requests.post",
        fail_if_hugging_face_is_called,
    )
    client = HuggingFaceClient()

    with pytest.raises(ExternalAnalysisServiceError):
        client.analyze_sentiment("Great service")


def test_missing_hugging_face_url_raises_external_analysis_service_error(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "test-token")
    monkeypatch.delenv("HF_SENTIMENT_MODEL_URL", raising=False)
    monkeypatch.setattr(
        "infrastructure.huggingface_client.requests.post",
        fail_if_hugging_face_is_called,
    )
    client = HuggingFaceClient()

    with pytest.raises(ExternalAnalysisServiceError):
        client.analyze_sentiment("Great service")


def test_empty_text_raises_external_analysis_service_error(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "test-token")
    monkeypatch.setenv("HF_SENTIMENT_MODEL_URL", "https://example.com/model")
    monkeypatch.setattr(
        "infrastructure.huggingface_client.requests.post",
        fail_if_hugging_face_is_called,
    )
    client = HuggingFaceClient()

    with pytest.raises(ExternalAnalysisServiceError):
        client.analyze_sentiment(" ")


def test_hugging_face_request_failure_raises_external_analysis_service_error(
    monkeypatch,
):
    def fake_post(*args, **kwargs):
        raise requests.RequestException("network failure")

    monkeypatch.setenv("HF_API_TOKEN", "test-token")
    monkeypatch.setenv("HF_SENTIMENT_MODEL_URL", "https://example.com/model")
    monkeypatch.setattr("infrastructure.huggingface_client.requests.post", fake_post)
    client = HuggingFaceClient()

    with pytest.raises(ExternalAnalysisServiceError):
        client.analyze_sentiment("Great service")


@pytest.mark.django_db
def test_get_survey_results_returns_zero_counts_for_survey_with_no_responses():
    provider = create_user("provider-empty-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary == {
        "survey_id": survey.survey_id,
        "response_count": 0,
        "positive_count": 0,
        "neutral_count": 0,
        "negative_count": 0,
        "positive_rate": 0,
        "neutral_rate": 0,
        "negative_rate": 0,
        "question_summaries": [],
    }


@pytest.mark.django_db
def test_get_survey_results_calculates_positive_neutral_and_negative_counts():
    survey = create_completed_sentiment_results()
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 1
    assert summary["neutral_count"] == 1
    assert summary["negative_count"] == 1


@pytest.mark.django_db
def test_get_survey_results_calculates_sentiment_rates_correctly():
    survey = create_completed_sentiment_results()
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_rate"] == pytest.approx(1 / 3)
    assert summary["neutral_rate"] == pytest.approx(1 / 3)
    assert summary["negative_rate"] == pytest.approx(1 / 3)


@pytest.mark.django_db
def test_positive_sentiment_result_linked_to_survey_is_counted():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Great service")
    create_sentiment_result(answer, SentimentLabel.POSITIVE)
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 1
    assert summary["neutral_count"] == 0
    assert summary["negative_count"] == 0


@pytest.mark.django_db
def test_neutral_sentiment_result_linked_to_survey_is_counted():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Average service")
    create_sentiment_result(answer, SentimentLabel.NEUTRAL)
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 0
    assert summary["neutral_count"] == 1
    assert summary["negative_count"] == 0


@pytest.mark.django_db
def test_negative_sentiment_result_linked_to_survey_is_counted():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Bad service")
    create_sentiment_result(answer, SentimentLabel.NEGATIVE)
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 0
    assert summary["neutral_count"] == 0
    assert summary["negative_count"] == 1


@pytest.mark.django_db
def test_sentiment_labels_are_counted_when_stored_as_mixed_case_strings():
    provider = create_user("provider-case-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    labels = ["positive", "Neutral", "NEGATIVE"]

    for index, label in enumerate(labels):
        respondent = create_user(
            f"respondent-case-summary-{index}@example.com",
            UserType.RESPONDENT,
        )
        response = create_response(survey, respondent)
        question = create_question(
            survey,
            QuestionType.OPEN_TEXT,
            text=f"Case question {index}?",
        )
        answer = create_answer(response, question, answer_value=f"Answer {index}")
        create_sentiment_result(answer, label)

    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 1
    assert summary["neutral_count"] == 1
    assert summary["negative_count"] == 1


@pytest.mark.django_db
def test_completed_status_enum_style_string_is_counted():
    survey, response = create_survey_response()
    question = create_question(survey, QuestionType.OPEN_TEXT)
    answer = create_answer(response, question, answer_value="Great service")
    create_sentiment_result(
        answer,
        "POSITIVE",
        status="AnalysisStatus.COMPLETED",
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert summary["positive_count"] == 1
    assert summary["neutral_count"] == 0
    assert summary["negative_count"] == 0


@pytest.mark.django_db
def test_multiple_choice_question_summary_returns_option_selection_counts():
    provider = create_user("provider-choice-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.MULTIPLE_CHOICE)
    yes_option = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="Yes", order_index=1)
    )
    no_option = QuestionRepository().save_option(
        QuestionOption(question=question, option_text="No", order_index=2)
    )

    for index, option in enumerate([yes_option, yes_option, no_option]):
        respondent = create_user(
            f"respondent-choice-summary-{index}@example.com",
            UserType.RESPONDENT,
        )
        response = create_response(survey, respondent)
        create_answer(response, question, selected_option=option)

    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)
    question_summary = summary["question_summaries"][0]

    assert question_summary["chart_type"] == "bar"
    assert question_summary["labels"] == ["Yes", "No"]
    assert question_summary["values"] == [2, 1]


@pytest.mark.django_db
def test_rating_scale_question_summary_returns_rating_counts():
    provider = create_user("provider-rating-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.RATING_SCALE)

    for index, rating in enumerate([5, 3, 5]):
        respondent = create_user(
            f"respondent-rating-summary-{index}@example.com",
            UserType.RESPONDENT,
        )
        response = create_response(survey, respondent)
        create_answer(response, question, rating_value=rating)

    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)
    question_summary = summary["question_summaries"][0]

    assert question_summary["chart_type"] == "rating"
    assert question_summary["labels"] == [1, 2, 3, 4, 5]
    assert question_summary["values"] == [0, 0, 1, 0, 2]


@pytest.mark.django_db
def test_open_text_question_summary_returns_submitted_text_answers():
    provider = create_user("provider-text-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)

    for index, text in enumerate(["Great service", "Clear process"]):
        respondent = create_user(
            f"respondent-text-summary-{index}@example.com",
            UserType.RESPONDENT,
        )
        response = create_response(survey, respondent)
        create_answer(response, question, answer_value=text)

    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)
    question_summary = summary["question_summaries"][0]

    assert question_summary["chart_type"] == "text"
    assert question_summary["text_answers"] == ["Great service", "Clear process"]


@pytest.mark.django_db
def test_get_survey_results_returns_question_summaries():
    provider = create_user("provider-question-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    question = create_question(survey, QuestionType.OPEN_TEXT)
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    summary = service.get_survey_results(survey.survey_id)

    assert "question_summaries" in summary
    assert summary["question_summaries"][0]["question_id"] == question.question_id


# ---------------------------------------------------------------------------
# Regression tests: one completed result linked to a survey must be counted
# These tests mirror the exact scenario that was reported as a dashboard bug.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_single_completed_positive_result_with_score_is_counted():
    """A COMPLETED POSITIVE result (score 0.95) must appear in the summary."""
    provider = create_user(
        "provider-reg-positive@example.com", UserType.SERVICE_PROVIDER
    )
    respondent = create_user(
        "respondent-reg-positive@example.com", UserType.RESPONDENT
    )
    survey = create_survey(provider, title="Regression Survey Positive")
    response = create_response(survey, respondent)
    question = create_question(survey, QuestionType.OPEN_TEXT, text="What did you like?")
    answer = create_answer(response, question, answer_value="i love this")
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.COMPLETED,
            sentiment_label=SentimentLabel.POSITIVE,
            sentiment_score=0.95,
            analyzed_at=timezone.now(),
        )
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    result = service.get_survey_results(survey.survey_id)

    assert result["positive_count"] == 1
    assert result["neutral_count"] == 0
    assert result["negative_count"] == 0
    assert result["response_count"] == 1


@pytest.mark.django_db
def test_single_completed_neutral_result_with_score_is_counted():
    """A COMPLETED NEUTRAL result (score 0.95) must appear in the summary."""
    provider = create_user(
        "provider-reg-neutral@example.com", UserType.SERVICE_PROVIDER
    )
    respondent = create_user(
        "respondent-reg-neutral@example.com", UserType.RESPONDENT
    )
    survey = create_survey(provider, title="Regression Survey Neutral")
    response = create_response(survey, respondent)
    question = create_question(survey, QuestionType.OPEN_TEXT, text="How was it?")
    answer = create_answer(response, question, answer_value="it was okay")
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.COMPLETED,
            sentiment_label=SentimentLabel.NEUTRAL,
            sentiment_score=0.95,
            analyzed_at=timezone.now(),
        )
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    result = service.get_survey_results(survey.survey_id)

    assert result["positive_count"] == 0
    assert result["neutral_count"] == 1
    assert result["negative_count"] == 0
    assert result["response_count"] == 1


@pytest.mark.django_db
def test_single_completed_negative_result_with_score_is_counted():
    """A COMPLETED NEGATIVE result (score 0.95) must appear in the summary."""
    provider = create_user(
        "provider-reg-negative@example.com", UserType.SERVICE_PROVIDER
    )
    respondent = create_user(
        "respondent-reg-negative@example.com", UserType.RESPONDENT
    )
    survey = create_survey(provider, title="Regression Survey Negative")
    response = create_response(survey, respondent)
    question = create_question(survey, QuestionType.OPEN_TEXT, text="What went wrong?")
    answer = create_answer(response, question, answer_value="i hate this")
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.COMPLETED,
            sentiment_label=SentimentLabel.NEGATIVE,
            sentiment_score=0.95,
            analyzed_at=timezone.now(),
        )
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    result = service.get_survey_results(survey.survey_id)

    assert result["positive_count"] == 0
    assert result["neutral_count"] == 0
    assert result["negative_count"] == 1
    assert result["response_count"] == 1


@pytest.mark.django_db
def test_pending_sentiment_result_is_not_counted():
    """A PENDING result must never be counted in any sentiment bucket."""
    provider = create_user(
        "provider-reg-pending@example.com", UserType.SERVICE_PROVIDER
    )
    respondent = create_user(
        "respondent-reg-pending@example.com", UserType.RESPONDENT
    )
    survey = create_survey(provider, title="Regression Survey Pending")
    response = create_response(survey, respondent)
    question = create_question(survey, QuestionType.OPEN_TEXT, text="Any comments?")
    answer = create_answer(response, question, answer_value="still processing")
    # PENDING: label and score are null per ID-15
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.PENDING,
            sentiment_label=None,
            sentiment_score=None,
            analyzed_at=None,
        )
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    result = service.get_survey_results(survey.survey_id)

    assert result["positive_count"] == 0
    assert result["neutral_count"] == 0
    assert result["negative_count"] == 0
    assert result["response_count"] == 1


@pytest.mark.django_db
def test_failed_sentiment_result_is_not_counted():
    """A FAILED result must never be counted in any sentiment bucket."""
    provider = create_user(
        "provider-reg-failed@example.com", UserType.SERVICE_PROVIDER
    )
    respondent = create_user(
        "respondent-reg-failed@example.com", UserType.RESPONDENT
    )
    survey = create_survey(provider, title="Regression Survey Failed")
    response = create_response(survey, respondent)
    question = create_question(survey, QuestionType.OPEN_TEXT, text="Any issues?")
    answer = create_answer(response, question, answer_value="error case")
    # FAILED: label and score are cleared per ID-15
    AnalysisRepository().save(
        SentimentAnalysisResult(
            answer=answer,
            status=AnalysisStatus.FAILED,
            sentiment_label=None,
            sentiment_score=None,
            analyzed_at=timezone.now(),
        )
    )
    service = AnalysisService(huggingface_client=FakeHuggingFaceClient())

    result = service.get_survey_results(survey.survey_id)

    assert result["positive_count"] == 0
    assert result["neutral_count"] == 0
    assert result["negative_count"] == 0
    assert result["response_count"] == 1


def create_completed_sentiment_results():
    provider = create_user("provider-summary@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider)
    labels = [
        {"label": "positive", "score": 0.9},
        {"label": "neutral", "score": 0.7},
        {"label": "negative", "score": 0.8},
    ]
    fake_client = FakeHuggingFaceClient(responses=labels)
    service = AnalysisService(huggingface_client=fake_client)

    for index in range(3):
        respondent = create_user(
            f"respondent-summary-{index}@example.com",
            UserType.RESPONDENT,
        )
        response = create_response(survey, respondent)
        question = create_question(survey, QuestionType.OPEN_TEXT, text=f"Question {index}?")
        create_answer(response, question, answer_value=f"Answer {index}")
        service.analyze_open_text_answers(response.response_id)

    return survey
