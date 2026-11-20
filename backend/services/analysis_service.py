from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

from core.enums import AnalysisStatus, Gender, Governorate, QuestionType, SentimentLabel
from core.exceptions import (
    AnalysisBadOutput,
    AnalysisUnavailable,
    ExternalAnalysisServiceError,
    ValidationError,
)
from infrastructure.sentiment_analyzer import build_analyzer
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services import disclosure
from services.survey_access import ensure_survey_owner
from services.text_language import detect_language


class AnalysisService:
    """Handles Sentiment analysis orchestration and survey analytics summaries."""

    RATING_LABELS = [1, 2, 3, 4, 5]
    MAX_TEXT_ANSWERS_SHOWN = 50

    # FR-05 group breakdown (board W-05b, DESIGN-INC2 3.6): the profile details a provider
    # may compare open answers by, read from the response's snapshot.
    GROUP_BY_DIMENSIONS = ("gender", "age", "governorate")
    NOT_STATED_LABEL = "Not stated"
    OTHER_GROUPS_LABEL = "Other groups (combined)"
    GENDER_LABELS = {Gender.FEMALE.value: Gender.FEMALE.label, Gender.MALE.value: Gender.MALE.label}
    GOVERNORATE_LABELS = {choice.value: choice.label for choice in Governorate}
    # (lowest age of the group, label); the last group has no upper bound.
    AGE_GROUPS = (
        (55, "55 and over"),
        (45, "45 to 54"),
        (35, "35 to 44"),
        (25, "25 to 34"),
        (18, "18 to 24"),
    )
    UNDER_18_LABEL = "Under 18"

    # Worker rules (T-9). A full batch ends well before LOCK_TIMEOUT, so a row that is
    # still being analysed is never reclaimed. Worst case per adapter: huggingface 8 calls
    # x 15 s client timeout = 2 min; local (float32) the manifest hashing and model load, about
    # 8 to 18 s once per process, plus 8 CPU calls at p95 89 ms per item
    # (evaluation/results/deployed_check.md), well under a minute.
    BATCH_SIZE = 8
    LOCK_TIMEOUT = timedelta(minutes=5)
    RETRY_DELAYS_SECONDS = (30, 120)  # after attempt 1 and attempt 2
    MAX_ATTEMPTS = 3
    NO_TEXT_CODE = "no_text"
    # A due row older than this means the worker is probably not running (W-05a hint).
    OVERDUE_AFTER = timedelta(minutes=2)

    def __init__(
        self,
        response_repository=None,
        analysis_repository=None,
        question_repository=None,
        analyzer=None,
        survey_repository=None,
    ):
        """Wire repositories and the sentiment analyzer; building the analyzer loads no model."""
        self.response_repository = response_repository or ResponseRepository()
        self.analysis_repository = analysis_repository or AnalysisRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.analyzer = analyzer or build_analyzer()
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

    def retry_failed(self, provider_user, survey_id):
        """Return the survey's FAILED results to the queue, due now; owner only, results open.

        A provider may retry a failure the worker does not retry on its own (for example
        a 402 once the account has credit again). While the results are locked (P-20) the
        provider sees no failure, so the page offers nothing to retry.
        """
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)
        response_count = self.response_repository.find_by_survey_id(survey_id).count()
        if not disclosure.results_open(response_count):
            raise ValidationError(f"Results open at {disclosure.MIN_GROUP_SIZE} responses.")
        return self.analysis_repository.reset_failed(survey_id, timezone.now())

    def analysis_overdue(self, survey_id):
        """Return whether the survey's analysis waits longer than the worker should take.

        Overdue when the earliest due time of a PENDING row is more than OVERDUE_AFTER
        ago, or a RUNNING row is locked for longer than LOCK_TIMEOUT. The due time is the
        retry time when one is set, so a retried or reset old answer is not overdue at once.
        """
        now = timezone.now()
        oldest_due = self.analysis_repository.oldest_due_at(survey_id)
        if oldest_due is not None and oldest_due < now - self.OVERDUE_AFTER:
            return True
        return self.analysis_repository.has_stale_running(survey_id, now - self.LOCK_TIMEOUT)

    def _analyse_claimed_result(self, result):
        """Set the outcome of one claimed result on the object (not saved here)."""
        text = result.answer.answer_value
        language = detect_language(text)
        if language is None:
            result.mark_skipped(self.NO_TEXT_CODE)
            return

        try:
            analysis = self.analyzer.analyze_sentiment(text)
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
            model_id=self.analyzer.model_id,
        )

    def get_survey_results(self, provider_user, survey_id, group_by=None):
        """Build survey analytics; below the P-20 threshold return only the locked state.

        The lock and response_count count every submitted response, so an exclusion never
        locks the results again (P-08). The charts and sentiment counts use the responses
        the provider has not excluded, and leave attention questions out.

        group_by (FR-05) is "gender", "age" or "governorate"; any other value means no
        breakdown. Each open-text question then gets its sentiment by group, with every
        group under MIN_GROUP_SIZE analysed answers pooled (P-15).
        """
        if group_by not in self.GROUP_BY_DIMENSIONS:
            group_by = None
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)

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

        sentiment_results = self.analysis_repository.find_included_by_survey_id(survey_id)
        questions = [
            question
            for question in self.question_repository.find_by_survey_id(survey_id)
            if not question.is_attention_check
        ]
        answers = self.response_repository.find_included_answers_by_survey_id(survey_id)

        positive_count = 0
        neutral_count = 0
        negative_count = 0
        failed_count = 0
        waiting_count = 0
        skipped_count = 0
        failed_codes = Counter()
        results_by_question_id = defaultdict(list)

        for result in sentiment_results:
            results_by_question_id[result.answer.question_id].append(result)
            status = self._normalized_value(result.status)
            if status == AnalysisStatus.FAILED.value:
                failed_count += 1
                failed_codes[result.error_code or ""] += 1
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
            "included_count": self.response_repository.count_included_by_survey_id(survey_id),
            "locked": False,
            "min_responses": min_responses,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "failed_count": failed_count,
            "waiting_count": waiting_count,
            "skipped_count": skipped_count,
            "failed_reasons": [
                {"code": code, "count": count}
                for code, count in sorted(failed_codes.items(), key=lambda item: (-item[1], item[0]))
            ],
            "analysis_overdue": self.analysis_overdue(survey_id),
            "positive_rate": self._rate(positive_count, completed_count),
            "neutral_rate": self._rate(neutral_count, completed_count),
            "negative_rate": self._rate(negative_count, completed_count),
            "group_by": group_by,
            "question_summaries": self._build_question_summaries(
                questions, answers, results_by_question_id, group_by
            ),
        }

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

    def _build_question_summaries(self, questions, answers, results_by_question_id, group_by):
        """Build question-level analytics summaries from submitted answers."""
        answers_by_question_id = defaultdict(list)
        for answer in answers:
            answers_by_question_id[answer.question_id].append(answer)

        return [
            self._question_summary(
                question,
                answers_by_question_id.get(question.question_id, []),
                results_by_question_id.get(question.question_id, []),
                group_by,
            )
            for question in questions
        ]

    def _question_summary(self, question, answers, sentiment_results, group_by):
        """Choose the correct analytics summary type for a question."""
        question_type = self._normalized_value(question.question_type)

        if question_type == QuestionType.MULTIPLE_CHOICE.value:
            return self._multiple_choice_summary(question, answers)
        if question_type == QuestionType.RATING_SCALE.value:
            return self._rating_summary(question, answers)
        return self._open_text_summary(question, answers, sentiment_results, group_by)

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

    def _open_text_summary(self, question, answers, sentiment_results, group_by):
        """Build the text answers, the sentiment and the optional breakdown of a question."""
        summary = self._base_question_summary(question, "text")
        text_answers = [
            answer.answer_value.strip()
            for answer in answers
            if isinstance(answer.answer_value, str) and answer.answer_value.strip()
        ]
        summary["text_answer_total"] = len(text_answers)
        summary["text_answers"] = text_answers[: self.MAX_TEXT_ANSWERS_SHOWN]

        completed = []
        not_analysed = 0
        for result in sentiment_results:
            status = self._normalized_value(result.status)
            if status in (
                AnalysisStatus.PENDING.value,
                AnalysisStatus.RUNNING.value,
                AnalysisStatus.FAILED.value,
            ):
                not_analysed += 1
            elif status == AnalysisStatus.COMPLETED.value and self._sentiment_key(result):
                completed.append(result)
        # The same counts as the survey panel: SKIPPED answers are left out of the total.
        counts = self._sentiment_counts(completed)
        summary["sentiment"] = {"total": counts["analysed"] + not_analysed, **counts}
        summary["breakdown"] = (
            self._sentiment_breakdown(completed, group_by) if group_by else None
        )
        return summary

    def _sentiment_key(self, result):
        """Return "positive", "neutral" or "negative" for a result's label, or None."""
        return {
            SentimentLabel.POSITIVE.value: "positive",
            SentimentLabel.NEUTRAL.value: "neutral",
            SentimentLabel.NEGATIVE.value: "negative",
        }.get(self._normalized_value(result.sentiment_label))

    def _sentiment_counts(self, completed):
        """Count completed results by sentiment."""
        counts = {"analysed": len(completed), "positive": 0, "neutral": 0, "negative": 0}
        for result in completed:
            counts[self._sentiment_key(result)] += 1
        return counts

    def _sentiment_breakdown(self, completed, group_by):
        """Group completed results by a snapshot detail and pool small groups (P-15).

        The pool is formed on analysed answers, the count every figure of a row describes.
        When fewer than two rows remain, no row is returned.
        """
        by_group = defaultdict(list)
        for result in completed:
            by_group[self._group_label(result.answer.response, group_by)].append(result)

        pooling = disclosure.pool_groups(
            {label: len(results) for label, results in by_group.items()}
        )
        rows = []
        if pooling["enough"]:
            rows = [
                {"label": label, **self._sentiment_counts(by_group[label]), "pooled": False}
                for label in pooling["shown"]
            ]
            if pooling["pooled"]:
                pooled_results = [
                    result for label in pooling["pooled"] for result in by_group[label]
                ]
                rows.append(
                    {
                        "label": self.OTHER_GROUPS_LABEL,
                        **self._sentiment_counts(pooled_results),
                        "pooled": True,
                    }
                )
        return {"dimension": group_by, "enough": pooling["enough"], "rows": rows}

    def _group_label(self, response, group_by):
        """Return the group of a response from its snapshot, taken when it was submitted."""
        if group_by == "gender":
            return self.GENDER_LABELS.get(response.snap_gender, self.NOT_STATED_LABEL)
        if group_by == "governorate":
            return self.GOVERNORATE_LABELS.get(response.snap_region, self.NOT_STATED_LABEL)
        age = response.snap_age
        if age is None:
            return self.NOT_STATED_LABEL
        for lowest, label in self.AGE_GROUPS:
            if age >= lowest:
                return label
        return self.UNDER_18_LABEL

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
