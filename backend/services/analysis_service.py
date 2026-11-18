from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

from core.enums import AnalysisStatus, QuestionType, SentimentLabel, UserType
from core.exceptions import (
    AnalysisBadOutput,
    AnalysisUnavailable,
    ExternalAnalysisServiceError,
    SurveyNotFound,
    UnauthorizedAction,
)
from infrastructure.huggingface_client import HuggingFaceClient
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services import disclosure
from services.text_language import detect_language


class AnalysisService:
    """Handles Sentiment analysis orchestration and survey analytics summaries."""

    RATING_LABELS = [1, 2, 3, 4, 5]
    MAX_TEXT_ANSWERS_SHOWN = 50

    # Worker rules (T-9). A full batch (8 calls x 15 s client timeout) ends well
    # before LOCK_TIMEOUT, so a row that is still being analysed is never reclaimed.
    BATCH_SIZE = 8
    LOCK_TIMEOUT = timedelta(minutes=5)
    RETRY_DELAYS_SECONDS = (30, 120)  # after attempt 1 and attempt 2
    MAX_ATTEMPTS = 3
    NO_TEXT_CODE = "no_text"

    def __init__(
        self,
        response_repository=None,
        analysis_repository=None,
        question_repository=None,
        huggingface_client=None,
        survey_repository=None,
    ):
        """Wire repositories and infrastructure used by analytics workflows."""
        self.response_repository = response_repository or ResponseRepository()
        self.analysis_repository = analysis_repository or AnalysisRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.huggingface_client = huggingface_client or HuggingFaceClient()
        self.survey_repository = survey_repository or SurveyRepository()

    def queue_open_text_answers(self, answers):
        """Store one PENDING result per saved open-text answer that has text."""
        pending_answers = [
            answer
            for answer in answers
            if answer.requires_sentiment_analysis()
            and isinstance(answer.answer_value, str)
            and answer.answer_value.strip()
        ]
        if not pending_answers:
            return []
        return self.analysis_repository.create_pending(pending_answers)

    def process_pending_batch(self, limit=BATCH_SIZE):
        """Claim due results, analyse them with no transaction open, store each outcome."""
        now = timezone.now()
        claimed, expired = self.analysis_repository.claim_batch(
            limit=limit,
            now=now,
            stale_before=now - self.LOCK_TIMEOUT,
            max_attempts=self.MAX_ATTEMPTS,
            expired_error_code=AnalysisUnavailable.error_code,
        )

        for result in claimed:
            self._analyse_claimed_result(result)
            # Each outcome is stored on its own; one failed write keeps the others.
            self.analysis_repository.update(result)

        return expired + claimed

    def sentiment_status_counts(self, survey_id):
        """Return analysed, waiting, failed and skipped counts and the oldest wait."""
        counts = Counter()
        for status, total in self.analysis_repository.count_by_status(survey_id).items():
            counts[self._normalized_value(status)] += total

        oldest = self.analysis_repository.oldest_waiting_submitted_at(survey_id)
        return {
            "analysed": counts[AnalysisStatus.COMPLETED.value],
            "waiting": counts[AnalysisStatus.PENDING.value]
            + counts[AnalysisStatus.RUNNING.value],
            "failed": counts[AnalysisStatus.FAILED.value],
            "skipped": counts[AnalysisStatus.SKIPPED.value],
            "oldest_waiting_seconds": (
                None if oldest is None else int((timezone.now() - oldest).total_seconds())
            ),
        }

    def retry_failed(self, provider_user, survey_id):
        """Return the survey's FAILED results to the queue; only the owner may do it."""
        self._ensure_survey_owner(provider_user, survey_id)
        return self.analysis_repository.reset_failed(survey_id)

    def _analyse_claimed_result(self, result):
        """Set the outcome of one claimed result on the object (not saved here)."""
        text = result.answer.answer_value
        language = detect_language(text)
        if language is None:
            result.mark_skipped(self.NO_TEXT_CODE)
            return

        try:
            analysis = self.huggingface_client.analyze_sentiment(text)
        except AnalysisUnavailable:
            if result.attempts >= self.MAX_ATTEMPTS:
                result.mark_failed(AnalysisUnavailable.error_code)
            else:
                delay = self.RETRY_DELAYS_SECONDS[result.attempts - 1]
                result.schedule_retry(timezone.now() + timedelta(seconds=delay))
            return
        except ExternalAnalysisServiceError as exc:
            # Config, payment and bad-output errors do not pass by waiting.
            result.mark_failed(exc.error_code)
            return

        label = self._map_external_label(analysis.get("label"))
        if label is None:
            result.mark_failed(AnalysisBadOutput.error_code)
            return

        result.mark_completed(
            label,
            analysis.get("score"),
            timezone.now(),
            language=language,
            model_id=self.huggingface_client.model_id,
        )

    def get_survey_results(self, provider_user, survey_id):
        """Build survey analytics; below the P-20 threshold return only the locked state."""
        self._ensure_survey_owner(provider_user, survey_id)

        response_count = self.response_repository.find_by_survey_id(survey_id).count()
        min_responses = disclosure.MIN_GROUP_SIZE
        if not disclosure.results_open(response_count):
            # P-20: no answer, result or question is read for a locked survey.
            return {
                "survey_id": survey_id,
                "response_count": response_count,
                "locked": True,
                "min_responses": min_responses,
            }

        sentiment_results = self.analysis_repository.find_by_survey_id(survey_id)
        questions = self.question_repository.find_by_survey_id(survey_id)
        answers = self.response_repository.find_answers_by_survey_id(survey_id)

        positive_count = 0
        neutral_count = 0
        negative_count = 0
        failed_count = 0
        waiting_count = 0
        skipped_count = 0

        for result in sentiment_results:
            status = self._normalized_value(result.status)
            if status == AnalysisStatus.FAILED.value:
                failed_count += 1
                continue
            if status in (AnalysisStatus.PENDING.value, AnalysisStatus.RUNNING.value):
                waiting_count += 1
                continue
            if status == AnalysisStatus.SKIPPED.value:
                skipped_count += 1
                continue

            if not self._is_completed_result(result.status):
                continue

            sentiment_label = self._normalized_value(result.sentiment_label)
            if sentiment_label == SentimentLabel.POSITIVE.value:
                positive_count += 1
            elif sentiment_label == SentimentLabel.NEUTRAL.value:
                neutral_count += 1
            elif sentiment_label == SentimentLabel.NEGATIVE.value:
                negative_count += 1

        completed_count = positive_count + neutral_count + negative_count

        return {
            "survey_id": survey_id,
            "response_count": response_count,
            "locked": False,
            "min_responses": min_responses,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "failed_count": failed_count,
            "waiting_count": waiting_count,
            "skipped_count": skipped_count,
            "positive_rate": self._rate(positive_count, completed_count),
            "neutral_rate": self._rate(neutral_count, completed_count),
            "negative_rate": self._rate(negative_count, completed_count),
            "question_summaries": self._build_question_summaries(questions, answers),
        }

    def _ensure_survey_owner(self, provider_user, survey_id):
        """Ensure only the provider who owns the survey can read its analytics."""
        if provider_user.user_type != UserType.SERVICE_PROVIDER:
            raise UnauthorizedAction("Only service providers can view survey analytics.")

        survey = self.survey_repository.find_by_id(survey_id)
        if survey is None:
            raise SurveyNotFound("Survey not found.")

        if survey.provider_id != provider_user.user_id:
            raise UnauthorizedAction("Only the survey owner can view survey analytics.")

    def _map_external_label(self, label):
        """Map an external sentiment label to an internal enum value."""
        if label is None:
            return None

        return {
            "POSITIVE": SentimentLabel.POSITIVE,
            "NEGATIVE": SentimentLabel.NEGATIVE,
            "NEUTRAL": SentimentLabel.NEUTRAL,
        }.get(self._normalized_value(label))

    def _is_completed_result(self, status):
        """Return whether a sentiment result is completed."""
        return self._normalized_value(status) == AnalysisStatus.COMPLETED.value

    def _build_question_summaries(self, questions, answers):
        """Build question-level analytics summaries from submitted answers."""
        answers_by_question_id = defaultdict(list)
        for answer in answers:
            answers_by_question_id[answer.question_id].append(answer)

        return [
            self._question_summary(
                question,
                answers_by_question_id.get(question.question_id, []),
            )
            for question in questions
        ]

    def _question_summary(self, question, answers):
        """Choose the correct analytics summary type for a question."""
        question_type = self._normalized_value(question.question_type)

        if question_type == QuestionType.MULTIPLE_CHOICE.value:
            return self._multiple_choice_summary(question, answers)
        if question_type == QuestionType.RATING_SCALE.value:
            return self._rating_summary(question, answers)
        return self._open_text_summary(question, answers)

    def _base_question_summary(self, question, chart_type):
        """Build the shared structure for a question analytics summary."""
        return {
            "question_id": question.question_id,
            "question_text": question.question_text,
            "question_type": self._normalized_value(question.question_type),
            "chart_type": chart_type,
            "labels": [],
            "values": [],
            "text_answers": [],
            "text_answer_total": 0,
        }

    def _multiple_choice_summary(self, question, answers):
        """Build option selection counts for a multiple-choice question."""
        summary = self._base_question_summary(question, "bar")
        options = self.question_repository.find_options_by_question_id(
            question.question_id,
        )
        selection_counts = Counter(
            answer.selected_option_id
            for answer in answers
            if answer.selected_option_id is not None
        )

        summary["labels"] = [option.option_text for option in options]
        summary["values"] = [
            selection_counts.get(option.option_id, 0)
            for option in options
        ]
        return summary

    def _rating_summary(self, question, answers):
        """Build rating counts for a rating-scale question."""
        summary = self._base_question_summary(question, "rating")
        rating_counts = Counter(
            answer.rating_value
            for answer in answers
            if answer.rating_value is not None
        )

        summary["labels"] = self.RATING_LABELS
        summary["values"] = [
            rating_counts.get(rating, 0)
            for rating in self.RATING_LABELS
        ]
        return summary

    def _open_text_summary(self, question, answers):
        """Build the submitted text answer list for an open-text question."""
        summary = self._base_question_summary(question, "text")
        text_answers = [
            answer.answer_value.strip()
            for answer in answers
            if isinstance(answer.answer_value, str) and answer.answer_value.strip()
        ]
        summary["text_answer_total"] = len(text_answers)
        summary["text_answers"] = text_answers[: self.MAX_TEXT_ANSWERS_SHOWN]
        return summary

    def _normalized_value(self, value):
        """Normalize enum-like values for comparison and reporting."""
        if value is None:
            return ""
        if hasattr(value, "value"):
            value = value.value

        normalized = str(value).strip().upper()
        if "." in normalized:
            return normalized.rsplit(".", 1)[-1]
        return normalized

    def _rate(self, count, total):
        """Calculate a safe ratio for chart-ready analytics rates."""
        if total == 0:
            return 0
        return count / total
