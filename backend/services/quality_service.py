import hashlib
import hmac
import re
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.models import ResponseQuality
from core.enums import QuestionType
from core.exceptions import QuestionNotFound, ResponseNotFound, ValidationError
from repositories.quality_repository import QualityRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services import disclosure, quality_rules
from services.survey_access import ensure_survey_owner


class QualityService:
    """FR-04: stores the evidence of a response at submit (Part 1); turns it into flags and a
    score on read and stores the provider's include or exclude decision (Part 2).

    Flags and scores are never stored (P-01) and never reach a respondent; nothing is
    excluded automatically (P-08).
    """

    MAX_ACTIVE_MS = 3_600_000
    # Slack between the app's active time and the server's wall time (DESIGN-INC2 2.4).
    WALL_TIME_SLACK = timedelta(seconds=10)
    DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

    def __init__(self, quality_repository=None, response_repository=None, survey_repository=None):
        """Wire the repositories of the evidence, the responses and the survey owner check."""
        self.quality_repository = quality_repository or QualityRepository()
        self.response_repository = response_repository or ResponseRepository()
        self.survey_repository = survey_repository or SurveyRepository()

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

    def evaluate_survey(self, provider_user, survey_id):
        """Return the quality verdict of every submitted response of a survey; owner only.

        Below disclosure.MIN_GROUP_SIZE responses only the locked state is returned and no
        evidence is read (P-20). Otherwise four queries run, whatever the number of
        responses: the survey, the response count, the responses with their evidence, and
        the answered question types. No entry holds a device hash, a timing, the RSI, a
        respondent id or a profile field (DESIGN-INC2 2.4, privacy limit 3).
        """
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)
        response_count = self.response_repository.find_by_survey_id(survey_id).count()
        if not disclosure.results_open(response_count):
            return {
                "survey_id": survey_id,
                "locked": True,
                "response_count": response_count,
                "min_responses": disclosure.MIN_GROUP_SIZE,
            }

        rows = self.quality_repository.find_evidence_by_survey_id(survey_id)
        answered = defaultdict(dict)
        for response_id, question_id, question_type in (
            self.quality_repository.find_answered_questions_by_survey_id(survey_id)
        ):
            answered[response_id][question_id] = question_type

        verdicts = quality_rules.evaluate(
            self._rules_input(row, answered[row["response_id"]]) for row in rows
        )
        responses = [
            {
                "response_id": row["response_id"],
                "submitted_at": row["submitted_at"],
                "is_excluded": row["is_excluded"],
                "status": verdict["status"],
                "flags": verdict["flags"],
                "not_checked": verdict["not_checked"],
                "score": verdict["score"],
                "band": verdict["band"],
                "active_ms": row["quality__active_ms"],
            }
            for row, verdict in zip(rows, verdicts)
        ]
        responses.sort(
            key=lambda entry: (
                entry["status"] == quality_rules.BEFORE_CHECKS,
                entry["score"] or 0,
                entry["response_id"],
            )
        )

        flag_counts = dict.fromkeys(quality_rules.FLAG_CODES, 0)
        not_checked_counts = dict.fromkeys(quality_rules.FLAG_CODES, 0)
        band_counts = dict.fromkeys(quality_rules.BANDS, 0)
        for entry in responses:
            for code in entry["flags"]:
                flag_counts[code] += 1
            for code in entry["not_checked"]:
                not_checked_counts[code] += 1
            if entry["band"] is not None:
                band_counts[entry["band"]] += 1

        return {
            "survey_id": survey_id,
            "locked": False,
            "rules_version": quality_rules.RULES_VERSION,
            "response_count": len(responses),
            "included_count": sum(1 for entry in responses if not entry["is_excluded"]),
            "before_checks_count": sum(
                1 for entry in responses if entry["status"] == quality_rules.BEFORE_CHECKS
            ),
            "flag_counts": flag_counts,
            "not_checked_counts": not_checked_counts,
            "band_counts": band_counts,
            "flagged_included_count": sum(
                1 for entry in responses if entry["flags"] and not entry["is_excluded"]
            ),
            "responses": responses,
        }

    def set_inclusion(self, provider_user, survey_id, response_ids, excluded):
        """Include or exclude responses of a survey; owner only, results open.

        Every id must belong to the survey, otherwise nothing changes. Returns the number
        of responses whose state changed.
        """
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)
        self._ensure_results_open(survey_id)
        if not isinstance(excluded, bool):
            raise ValidationError("Excluded must be true or false.")
        if not isinstance(response_ids, (list, tuple, set)) or any(
            type(response_id) is not int for response_id in response_ids
        ):
            raise ValidationError("Response ids must be a list of integers.")
        return self._apply_inclusion(survey_id, set(response_ids), excluded)

    def exclude_flagged(self, provider_user, survey_id):
        """Exclude the responses that are flagged and included now (board W-04); return the count."""
        evaluation = self.evaluate_survey(provider_user, survey_id)
        if evaluation["locked"]:
            raise ValidationError(self._locked_message())
        flagged = {
            entry["response_id"]
            for entry in evaluation["responses"]
            if entry["flags"] and not entry["is_excluded"]
        }
        return self._apply_inclusion(survey_id, flagged, True)

    def include_all(self, provider_user, survey_id):
        """Include every excluded response of a survey; return the count."""
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)
        self._ensure_results_open(survey_id)
        excluded = set(self.response_repository.find_excluded_ids_by_survey_id(survey_id))
        return self._apply_inclusion(survey_id, excluded, False)

    def set_response_inclusion(self, provider_user, survey_id, number, excluded):
        """Exclude or include the response at a number (board W-07); return 1 when it changed, else 0.

        A response collected before quality checks has no score and cannot be excluded here.
        Nothing changes on any refusal.
        """
        ensure_survey_owner(self.survey_repository, provider_user, survey_id)
        self._ensure_results_open(survey_id)
        if not isinstance(excluded, bool):
            raise ValidationError("Excluded must be true or false.")
        found = self.response_repository.find_by_number(survey_id, number)
        if found is None:
            raise ResponseNotFound("Response does not belong to this survey.")
        if excluded and not found["has_evidence"]:
            raise ValidationError(
                "This response was collected before quality checks. "
                "It has no score and stays included."
            )
        return self._apply_inclusion(survey_id, {found["response_id"]}, excluded)

    def _apply_inclusion(self, survey_id, response_ids, excluded):
        """Set the inclusion of the given responses in one bulk update; return how many changed."""
        if not response_ids:
            return 0
        with transaction.atomic():
            states = self.response_repository.lock_exclusion_states(survey_id, response_ids)
            if len(states) != len(response_ids):
                raise ResponseNotFound("Response does not belong to this survey.")
            changed = [
                response_id for response_id, is_excluded in states.items() if is_excluded != excluded
            ]
            if changed:
                self.response_repository.set_excluded(
                    changed, excluded, timezone.now() if excluded else None
                )
        return len(changed)

    def _rules_input(self, row, answered):
        """Return the plain rules input of one evidence row."""
        evidence = None
        if row["quality__quality_id"] is not None:
            evidence = {
                "timings": row["quality__timings"],
                "attention_total": row["quality__attention_total"],
                "attention_failed": row["quality__attention_failed"],
                "rating_count": row["quality__rating_count"],
                "rating_all_same": row["quality__rating_all_same"],
                "device_hash": row["quality__device_hash"],
                "signals_ok": row["quality__signals_ok"],
            }
        return {
            "response_id": row["response_id"],
            "respondent_id": row["respondent_id"],
            "answered": answered,
            "evidence": evidence,
        }

    def _ensure_results_open(self, survey_id):
        """Refuse a change while the survey's results are locked (P-20)."""
        response_count = self.response_repository.find_by_survey_id(survey_id).count()
        if not disclosure.results_open(response_count):
            raise ValidationError(self._locked_message())

    def _locked_message(self):
        """Return the message of a refused change while results are locked."""
        return f"Results open at {disclosure.MIN_GROUP_SIZE} responses."
