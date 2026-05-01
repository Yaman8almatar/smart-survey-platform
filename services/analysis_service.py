from collections import Counter, defaultdict

from django.utils import timezone

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus, QuestionType, SentimentLabel
from core.exceptions import ExternalAnalysisServiceError
from infrastructure.huggingface_client import HuggingFaceClient
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository


class AnalysisService:
    """Handles Sentiment analysis orchestration and survey analytics summaries."""

    RATING_LABELS = [1, 2, 3, 4, 5]

    def __init__(
        self,
        response_repository=None,
        analysis_repository=None,
        question_repository=None,
        huggingface_client=None,
    ):
        """Wire repositories and infrastructure used by analytics workflows."""
        self.response_repository = response_repository or ResponseRepository()
        self.analysis_repository = analysis_repository or AnalysisRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.huggingface_client = huggingface_client or HuggingFaceClient()

    def analyze_open_text_answers(self, response_id):
        """Run sentiment analysis for open-text answers through the infrastructure client."""
        results = []
        answers = self.response_repository.find_answers_by_response_id(response_id)

        for answer in answers:
            if not answer.requires_sentiment_analysis():
                continue

            result = self._get_or_create_pending_result(answer)

            try:
                # Hugging Face integration is isolated behind the infrastructure client.
                analysis = self.huggingface_client.analyze_sentiment(answer.answer_value)
                label = self._map_external_label(analysis.get("label"))
                if label is None:
                    raise ExternalAnalysisServiceError("Unknown sentiment label.")

                result.mark_completed(label, analysis.get("score"), timezone.now())
            except ExternalAnalysisServiceError:
                result.mark_failed()

            results.append(self.analysis_repository.update(result))

        return results

    def get_survey_results(self, survey_id):
        """Build survey analytics including sentiment counts and question-level summaries."""
        responses = self.response_repository.find_by_survey_id(survey_id)
        sentiment_results = self.analysis_repository.find_by_survey_id(survey_id)
        questions = self.question_repository.find_by_survey_id(survey_id)
        answers = self.response_repository.find_answers_by_survey_id(survey_id)

        response_count = responses.count()
        positive_count = 0
        neutral_count = 0
        negative_count = 0

        for result in sentiment_results:
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
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "positive_rate": self._rate(positive_count, completed_count),
            "neutral_rate": self._rate(neutral_count, completed_count),
            "negative_rate": self._rate(negative_count, completed_count),
            "question_summaries": self._build_question_summaries(questions, answers),
        }

    def _get_or_create_pending_result(self, answer):
        """Prepare a pending sentiment result before external analysis runs."""
        result = self.analysis_repository.find_by_answer_id(answer.answer_id)
        if result is None:
            result = SentimentAnalysisResult(answer=answer, status=AnalysisStatus.PENDING)
            return self.analysis_repository.save(result)

        result.status = AnalysisStatus.PENDING
        result.sentiment_label = None
        result.sentiment_score = None
        result.analyzed_at = None
        return self.analysis_repository.update(result)

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
        summary["text_answers"] = [
            answer.answer_value.strip()
            for answer in answers
            if isinstance(answer.answer_value, str) and answer.answer_value.strip()
        ]
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
