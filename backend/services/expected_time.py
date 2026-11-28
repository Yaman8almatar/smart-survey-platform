"""FR-08 expected time of a survey (DESIGN-FR08): plain Python, no Django import.

A survey with enough valid responses shows the median of their active times; any other
survey shows an estimate from its question types.
"""

import math
from statistics import median

from services import quality_rules

# Basis: team convention (DESIGN-FR08 choice 2): seconds a respondent needs per question type.
SECONDS_PER_QUESTION = {"MULTIPLE_CHOICE": 10, "RATING_SCALE": 8, "OPEN_TEXT": 40}

# The same bar as the relative speed index: a median of fewer responses is too unstable.
MIN_VALID_RESPONSES = quality_rules.RSI_MIN_RESPONSES

_MS_PER_MINUTE = 60_000
_SECONDS_PER_MINUTE = 60


def expected_minutes(type_counts, valid_active_ms):
    """Return whole minutes, rounded up and never under 1.

    type_counts: {question_type: count}; valid_active_ms: active times in milliseconds of the
    survey's valid responses.
    """
    if len(valid_active_ms) >= MIN_VALID_RESPONSES:
        minutes = math.ceil(median(valid_active_ms) / _MS_PER_MINUTE)
    else:
        seconds = sum(
            SECONDS_PER_QUESTION[question_type] * count
            for question_type, count in type_counts.items()
        )
        minutes = math.ceil(seconds / _SECONDS_PER_MINUTE)
    return max(1, minutes)
