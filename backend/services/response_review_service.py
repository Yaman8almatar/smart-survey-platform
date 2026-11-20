from core.enums import AnalysisStatus, QuestionType, SentimentLabel
from core.exceptions import ResponseNotFound
from repositories.analysis_repository import AnalysisRepository
from repositories.question_repository import QuestionRepository
from repositories.response_repository import RESPONSE_NUMBER_ORDER, ResponseRepository
from services import quality_rules
from services.quality_service import QualityService

SHOW_VALUES = ("all", "included", "excluded", "flagged")
ORDER_VALUES = ("score", "newest", "oldest")
OPEN_ANSWER_KEYS = ("positive", "neutral", "negative", "waiting", "failed")
LABEL_KEYS = {
    SentimentLabel.POSITIVE: "positive",
    SentimentLabel.NEUTRAL: "neutral",
    SentimentLabel.NEGATIVE: "negative",
}
WAITING_STATUSES = (AnalysisStatus.PENDING, AnalysisStatus.RUNNING)


class ResponseReviewService:
    """FR-07 and FR-09 (board W-07): the survey's responses one by one, each under a number.

    A number is the position of a response in RESPONSE_NUMBER_ORDER. No result holds a
    response id, a respondent id, a profile field, a device hash, the timings or the time
    of day; the verdicts come from QualityService.evaluate_survey (P-20 lock, owner check).
    """

    def __init__(
        self,
        quality_service=None,
        response_repository=None,
        analysis_repository=None,
        question_repository=None,
    ):
        """Wire the quality service and the repositories of responses, sentiment and questions."""
        self.quality_service = quality_service or QualityService()
        self.response_repository = response_repository or ResponseRepository()
        self.analysis_repository = analysis_repository or AnalysisRepository()
        self.question_repository = question_repository or QuestionRepository()

    def list_responses(self, provider_user, survey_id, show="all", order="score"):
        """Return the numbered rows of a survey's responses, filtered and ordered; owner only.

        Five queries, whatever the number of responses. An unknown show or order falls back
        to the default, and the result says which value was used.
        """
        evaluation = self.quality_service.evaluate_survey(provider_user, survey_id)
        if evaluation["locked"]:
            return evaluation

        show = show if show in SHOW_VALUES else "all"
        order = order if order in ORDER_VALUES else "score"

        open_answers = {}
        for response_id, status, label in self.analysis_repository.find_statuses_by_survey_id(
            survey_id
        ):
            key = self._open_answer_key(status, label)
            if key is None:
                continue
            counts = open_answers.setdefault(response_id, dict.fromkeys(OPEN_ANSWER_KEYS, 0))
            counts[key] += 1

        rows = [
            {
                "number": number,
                "submitted_at": entry["submitted_at"],
                "status": entry["status"],
                "score": entry["score"],
                "band": entry["band"],
                "flags": entry["flags"],
                "is_excluded": entry["is_excluded"],
                "open_answers": open_answers.get(
                    entry["response_id"], dict.fromkeys(OPEN_ANSWER_KEYS, 0)
                ),
            }
            for number, entry in self._numbered(evaluation["responses"])
            if self._shown(entry, show)
        ]
        rows.sort(key=self._order_key(order))

        total = evaluation["response_count"]
        included = evaluation["included_count"]
        return {
            "locked": False,
            "total": total,
            "included": included,
            "excluded": total - included,
            "show": show,
            "order": order,
            "rows": rows,
        }

    def get_response(self, provider_user, survey_id, number):
        """Return one response by its number with its answers and quality verdict; owner only.

        Eight queries, whatever the number of responses or questions.
        """
        evaluation = self.quality_service.evaluate_survey(provider_user, survey_id)
        if evaluation["locked"]:
            return evaluation

        numbered = self._numbered(evaluation["responses"])
        total = len(numbered)
        if type(number) is not int or not 1 <= number <= total:
            raise ResponseNotFound("Response does not belong to this survey.")
        entry = numbered[number - 1][1]
        response_id = entry["response_id"]

        questions = list(self.question_repository.find_by_survey_id_with_options(survey_id))
        answers = {
            answer.question_id: answer
            for answer in self.response_repository.find_answers_with_options_by_response_id(
                response_id
            )
        }
        sentiments = self.analysis_repository.find_by_response_id(response_id)

        return {
            "locked": False,
            "number": number,
            "total": total,
            "submitted_at": entry["submitted_at"],
            "active_ms": entry["active_ms"],
            "is_excluded": entry["is_excluded"],
            "status": entry["status"],
            "score": entry["score"],
            "band": entry["band"],
            "flags": entry["flags"],
            "not_checked": entry["not_checked"],
            "previous_number": number - 1 if number > 1 else None,
            "next_number": number + 1 if number < total else None,
            "answers": [
                self._answer_item(position, question, answers.get(question.question_id), sentiments)
                for position, question in enumerate(questions, start=1)
            ],
        }

    def _numbered(self, entries):
        """Return [(number, entry)] in RESPONSE_NUMBER_ORDER, numbered from 1."""
        ordered = sorted(
            entries, key=lambda entry: tuple(entry[key] for key in RESPONSE_NUMBER_ORDER)
        )
        return list(enumerate(ordered, start=1))

    def _shown(self, entry, show):
        """Return whether an evaluation entry passes the show filter."""
        if show == "included":
            return not entry["is_excluded"]
        if show == "excluded":
            return entry["is_excluded"]
        if show == "flagged":
            return bool(entry["flags"])
        return True

    def _order_key(self, order):
        """Return the sort key of the rows for an order value."""
        if order == "newest":
            return lambda row: -row["number"]
        if order == "oldest":
            return lambda row: row["number"]
        return lambda row: (
            row["status"] == quality_rules.BEFORE_CHECKS,
            row["score"] or 0,
            row["number"],
        )

    def _open_answer_key(self, status, label):
        """Return the open-answers count key of one sentiment result, or None when left out."""
        if status == AnalysisStatus.COMPLETED:
            return LABEL_KEYS.get(label)
        if status in WAITING_STATUSES:
            return "waiting"
        if status == AnalysisStatus.FAILED:
            return "failed"
        return None

    def _answer_item(self, position, question, answer, sentiments):
        """Return the display data of one question and this response's answer to it."""
        value = self._answer_value(question, answer)
        expected_answer = self.quality_service._expected_answer(question)
        is_attention_check = question.is_attention_check and expected_answer is not None
        expected = None
        if is_attention_check:
            expected = expected_answer
            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                expected = next(
                    (
                        option.option_text
                        for option in question.options.all()
                        if option.option_id == expected_answer
                    ),
                    None,
                )

        sentiment = None
        if question.question_type == QuestionType.OPEN_TEXT and answer is not None:
            status, label = sentiments.get(answer.answer_id, (None, None))
            sentiment = self._open_answer_key(status, label)

        return {
            "position": position,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "answered": value is not None and value != "",
            "value": value,
            "is_attention_check": is_attention_check,
            "expected": expected,
            "sentiment": sentiment,
        }

    def _answer_value(self, question, answer):
        """Return the option text, the rating or the text of an answer, or None."""
        if answer is None:
            return None
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return answer.selected_option.option_text if answer.selected_option else None
        if question.question_type == QuestionType.RATING_SCALE:
            return answer.rating_value
        return answer.answer_value
