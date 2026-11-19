import hashlib
import hmac
import re
from datetime import timedelta

from django.conf import settings

from apps.core.models import ResponseQuality
from core.enums import QuestionType
from core.exceptions import QuestionNotFound, ValidationError
from repositories.quality_repository import QualityRepository


class QualityService:
    """FR-04 Part 1: validates and stores the evidence of a response; no flag, no score (P-01)."""

    MAX_ACTIVE_MS = 3_600_000
    # Slack between the app's active time and the server's wall time (DESIGN-INC2 2.4).
    WALL_TIME_SLACK = timedelta(seconds=10)
    DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

    def __init__(self, quality_repository=None):
        """Wire the repository that writes the evidence row."""
        self.quality_repository = quality_repository or QualityRepository()

    def clean_timings(self, timings, question_ids):
        """Return the timings as plain entries; reject malformed, repeated or foreign ones."""
        if not isinstance(timings, list):
            raise ValidationError("Timings must be provided as a list.")

        cleaned = []
        seen = set()
        for entry in timings:
            if not isinstance(entry, dict):
                raise ValidationError("Each timing must be a dictionary.")
            question_id = entry.get("question_id")
            active_ms = entry.get("active_ms")
            if type(question_id) is not int:
                raise ValidationError("Each timing must include an integer question_id.")
            if type(active_ms) is not int or not 0 <= active_ms <= self.MAX_ACTIVE_MS:
                raise ValidationError(
                    f"Timing active_ms must be an integer from 0 to {self.MAX_ACTIVE_MS}."
                )
            if question_id in seen:
                raise ValidationError("Duplicate timings for the same question are invalid.")
            if question_id not in question_ids:
                raise QuestionNotFound("Question does not belong to this survey.")
            seen.add(question_id)
            cleaned.append({"question_id": question_id, "active_ms": active_ms})
        return cleaned

    def clean_device_id(self, device_id):
        """Return the device id unchanged, or reject one that does not match the format."""
        if device_id is None:
            return None
        if not isinstance(device_id, str) or not self.DEVICE_ID_PATTERN.match(device_id):
            # The message never repeats the value: the raw id is logged nowhere.
            raise ValidationError("Device id must be 16 to 64 letters, digits, - or _.")
        return device_id

    def hash_device_id(self, device_id):
        """Return the hex HMAC-SHA256 of the device id with DEVICE_HASH_KEY, or ""."""
        if not device_id:
            return ""
        return hmac.new(
            settings.DEVICE_HASH_KEY.encode(),
            device_id.encode(),
            hashlib.sha256,
        ).hexdigest()

    def capture(self, response, questions, answers, timings, device_id, started_at):
        """Store the evidence row of a just-saved response; call inside the submit transaction.

        Missing or inconsistent evidence never rejects the response (DESIGN-INC2 2.4): it
        only sets signals_ok to false.
        """
        answer_by_question = {answer.question_id: answer for answer in answers}
        active_ms = sum(entry["active_ms"] for entry in timings) if timings else None

        attention_total = 0
        attention_failed = 0
        ratings = []
        for question in questions:
            answer = answer_by_question.get(question.question_id)
            if question.is_attention_check:
                expected = self._expected_answer(question)
                if expected is None:
                    continue
                attention_total += 1
                if self._given_answer(question, answer) != expected:
                    attention_failed += 1
            elif question.question_type == QuestionType.RATING_SCALE and answer is not None:
                ratings.append(answer.rating_value)

        signals_ok = bool(
            timings
            and device_id
            and started_at is not None
            and timedelta(milliseconds=active_ms)
            <= (response.submitted_at - started_at) + self.WALL_TIME_SLACK
        )

        return self.quality_repository.save(
            ResponseQuality(
                response=response,
                survey_id=response.survey_id,
                timings=list(timings),
                active_ms=active_ms,
                attention_total=attention_total,
                attention_failed=attention_failed,
                rating_count=len(ratings),
                rating_all_same=bool(ratings) and len(set(ratings)) == 1,
                device_hash=self.hash_device_id(device_id),
                signals_ok=signals_ok,
            )
        )

    def _expected_answer(self, question):
        """Return the expected option id or rating of an attention question, or None."""
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return question.expected_option_id
        if question.question_type == QuestionType.RATING_SCALE:
            return question.expected_rating
        return None

    def _given_answer(self, question, answer):
        """Return the option id or rating the respondent gave, or None."""
        if answer is None:
            return None
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return answer.selected_option_id
        return answer.rating_value
