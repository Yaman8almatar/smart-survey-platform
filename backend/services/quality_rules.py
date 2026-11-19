"""FR-04 quality rules (DESIGN-INC2 section 2, P-01): stored evidence in, verdicts out.

Plain Python on plain data: no Django, model, repository or service import, so the rules
run and are tested without a database. Flags, scores and bands are never stored; they are
derived on read from the evidence of every submitted response of one survey, whatever the
provider decided to include (P-08), so an include or exclude never changes a verdict.

Input of evaluate(), one dictionary per submitted response:
    {
        "response_id": int,
        "respondent_id": int,
        "answered": {question_id: question_type},  # the questions this response answered
        "evidence": None or {                      # None: collected before FR-04
            "timings": [{"question_id": int, "active_ms": int}, ...],
            "attention_total": int,
            "attention_failed": int,
            "rating_count": int,
            "rating_all_same": bool,
            "device_hash": str,
            "signals_ok": bool,
        },
    }
"""

from collections import defaultdict
from statistics import median

RULES_VERSION = 1

# Flag codes, in the order every verdict lists them.
ATTENTION_FAILED = "ATTENTION_FAILED"
SPEEDING = "SPEEDING"
SIGNALS_MISSING = "SIGNALS_MISSING"
DUPLICATE_DEVICE = "DUPLICATE_DEVICE"
STRAIGHT_LINING = "STRAIGHT_LINING"
FLAG_CODES = (ATTENTION_FAILED, SPEEDING, SIGNALS_MISSING, DUPLICATE_DEVICE, STRAIGHT_LINING)

# Bands.
CLEAN = "CLEAN"
CHECK = "CHECK"
LOW = "LOW"
BANDS = (CLEAN, CHECK, LOW)

# Verdict status.
EVALUATED = "evaluated"
BEFORE_CHECKS = "before_checks"

# Question types answered by a click; the plain strings of core.enums.QuestionType.
CLOSED_QUESTION_TYPES = frozenset({"MULTIPLE_CHOICE", "RATING_SCALE"})

# SPEEDING rule (a), the floor. Basis: Huang et al. (2012), "Detecting and deterring
# insufficient effort responding to surveys", about 2 seconds per item.
FAST_ANSWER_MS = 2_000  # an answer under this is fast; 2,000 ms itself is not
# Basis: team convention; fewer timed closed answers say too little.
FLOOR_MIN_TIMED_CLOSED = 3
# Basis: team convention; flagged when at least this share of them is fast.
FAST_SHARE = 0.5

# SPEEDING rule (b), the relative speed index. Basis: Leiner (2019), "Too fast, too
# straight, too weird", Survey Research Methods 13(3): factor = median time / own time,
# capped, averaged over the pages; 2.0 marks a response twice as fast as the typical one.
RSI_THRESHOLD = 2.0
RSI_FACTOR_CAP = 3
# Basis: team convention; a median of fewer responses is too unstable.
RSI_MIN_RESPONSES = 20
# Basis: team convention; keeps a 0 ms timing from dividing by zero or dominating.
RSI_TIME_FLOOR_MS = 100

# STRAIGHT_LINING. Basis: team convention; fewer ratings can be all the same by chance.
STRAIGHT_LINING_MIN_RATINGS = 5

# Score. Basis: team convention (DESIGN-INC2 section 2).
MAX_SCORE = 100
ATTENTION_PENALTY = 40  # per failed attention check
ATTENTION_PENALTY_MAX_FAILED = 2  # a third failed check costs nothing more
SPEEDING_PENALTY = 30
SIGNALS_MISSING_PENALTY = 30
DUPLICATE_DEVICE_PENALTY = 20
STRAIGHT_LINING_PENALTY = 10
CHECK_MIN_SCORE = 60  # CLEAN at 100, CHECK from 60 to 99, LOW under 60


def evaluate(evidences):
    """Return one verdict per response of one survey, in the input order.

    A verdict is {"response_id", "status", "flags", "not_checked", "score", "band"};
    a response without evidence has status BEFORE_CHECKS, no flag, no score and no band.
    """
    evidences = list(evidences)
    timed = {entry["response_id"]: _timed_answers(entry) for entry in evidences}

    signals_ok = [
        entry
        for entry in evidences
        if entry["evidence"] is not None and entry["evidence"]["signals_ok"]
    ]
    medians = None
    if len(signals_ok) >= RSI_MIN_RESPONSES:
        medians = _question_medians(timed[entry["response_id"]] for entry in signals_ok)

    respondents_by_hash = defaultdict(set)
    for entry in evidences:
        if entry["evidence"] is not None and entry["evidence"]["device_hash"]:
            respondents_by_hash[entry["evidence"]["device_hash"]].add(entry["respondent_id"])

    return [
        _verdict(entry, timed[entry["response_id"]], medians, respondents_by_hash)
        for entry in evidences
    ]


def score(flags, attention_failed):
    """Return 100 minus the penalties of the flags, never under 0."""
    penalty = 0
    if ATTENTION_FAILED in flags:
        penalty += ATTENTION_PENALTY * min(attention_failed, ATTENTION_PENALTY_MAX_FAILED)
    if SPEEDING in flags:
        penalty += SPEEDING_PENALTY
    if SIGNALS_MISSING in flags:
        penalty += SIGNALS_MISSING_PENALTY
    if DUPLICATE_DEVICE in flags:
        penalty += DUPLICATE_DEVICE_PENALTY
    if STRAIGHT_LINING in flags:
        penalty += STRAIGHT_LINING_PENALTY
    return max(0, MAX_SCORE - penalty)


def band(value):
    """Return the band of a score."""
    if value >= MAX_SCORE:
        return CLEAN
    if value >= CHECK_MIN_SCORE:
        return CHECK
    return LOW


def _verdict(entry, timed, medians, respondents_by_hash):
    """Return the verdict of one response."""
    evidence = entry["evidence"]
    if evidence is None:
        return {
            "response_id": entry["response_id"],
            "status": BEFORE_CHECKS,
            "flags": [],
            "not_checked": [],
            "score": None,
            "band": None,
        }

    flagged = set()
    not_checked = set()

    if evidence["attention_total"] >= 1:
        if evidence["attention_failed"] >= 1:
            flagged.add(ATTENTION_FAILED)
    else:
        not_checked.add(ATTENTION_FAILED)

    if evidence["signals_ok"]:
        speeding = _speeding(timed, entry["answered"], medians)
        if speeding is None:
            not_checked.add(SPEEDING)
        elif speeding:
            flagged.add(SPEEDING)
    else:
        # The timings cannot be trusted, so SPEEDING is not judged on them.
        flagged.add(SIGNALS_MISSING)
        not_checked.add(SPEEDING)

    device_hash = evidence["device_hash"]
    if device_hash:
        if respondents_by_hash[device_hash] - {entry["respondent_id"]}:
            flagged.add(DUPLICATE_DEVICE)
    else:
        not_checked.add(DUPLICATE_DEVICE)

    if evidence["rating_count"] >= STRAIGHT_LINING_MIN_RATINGS:
        if evidence["rating_all_same"]:
            flagged.add(STRAIGHT_LINING)
    else:
        not_checked.add(STRAIGHT_LINING)

    flags = [code for code in FLAG_CODES if code in flagged]
    value = score(flags, evidence["attention_failed"])
    return {
        "response_id": entry["response_id"],
        "status": EVALUATED,
        "flags": flags,
        "not_checked": [code for code in FLAG_CODES if code in not_checked],
        "score": value,
        "band": band(value),
    }


def _timed_answers(entry):
    """Return {question_id: active_ms} for the answered questions that have a timing."""
    if entry["evidence"] is None:
        return {}
    answered = entry["answered"]
    return {
        timing["question_id"]: timing["active_ms"]
        for timing in entry["evidence"]["timings"]
        if timing["question_id"] in answered
    }


def _question_medians(timed_rows):
    """Return {question_id: median active_ms} over the given timed answers."""
    times = defaultdict(list)
    for timed in timed_rows:
        for question_id, active_ms in timed.items():
            times[question_id].append(active_ms)
    return {question_id: median(values) for question_id, values in times.items()}


def _speeding(timed, answered, medians):
    """Return True or False when rule (a) or (b) could run, otherwise None."""
    outcomes = []

    closed = [
        active_ms
        for question_id, active_ms in timed.items()
        if answered[question_id] in CLOSED_QUESTION_TYPES
    ]
    if len(closed) >= FLOOR_MIN_TIMED_CLOSED:
        fast = sum(1 for active_ms in closed if active_ms < FAST_ANSWER_MS)
        outcomes.append(fast >= FAST_SHARE * len(closed))

    if medians is not None and timed:
        factors = [
            min(medians[question_id] / max(active_ms, RSI_TIME_FLOOR_MS), RSI_FACTOR_CAP)
            for question_id, active_ms in timed.items()
        ]
        outcomes.append(sum(factors) / len(factors) >= RSI_THRESHOLD)

    if not outcomes:
        return None
    return any(outcomes)
