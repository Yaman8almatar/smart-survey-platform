"""FR-04 Part 2 (TASK-42): the quality rules on plain data; no database is used here."""

import ast
from pathlib import Path

import pytest

from services import quality_rules as rules
from services.quality_rules import (
    ATTENTION_FAILED,
    BEFORE_CHECKS,
    CHECK,
    CLEAN,
    DUPLICATE_DEVICE,
    EVALUATED,
    FLAG_CODES,
    LOW,
    SIGNALS_MISSING,
    SPEEDING,
    STRAIGHT_LINING,
    evaluate,
)

MC = "MULTIPLE_CHOICE"
RS = "RATING_SCALE"
OT = "OPEN_TEXT"


def response(
    response_id=1,
    respondent_id=None,
    answered=None,
    timings=None,
    signals_ok=True,
    attention_total=0,
    attention_failed=0,
    rating_count=0,
    rating_all_same=False,
    device_hash="",
):
    """Return one rules input; answered is {question_id: type}, timings {question_id: ms}."""
    return {
        "response_id": response_id,
        "respondent_id": respondent_id if respondent_id is not None else 1000 + response_id,
        "answered": dict(answered or {}),
        "evidence": {
            "timings": [
                {"question_id": question_id, "active_ms": active_ms}
                for question_id, active_ms in (timings or {}).items()
            ],
            "attention_total": attention_total,
            "attention_failed": attention_failed,
            "rating_count": rating_count,
            "rating_all_same": rating_all_same,
            "device_hash": device_hash,
            "signals_ok": signals_ok,
        },
    }


def closed_response(times, response_id=1, **kwargs):
    """Return a response that answered one closed question per given time."""
    answered = {index: (MC if index % 2 else RS) for index in range(1, len(times) + 1)}
    timings = dict(zip(answered, times))
    return response(response_id, answered=answered, timings=timings, **kwargs)


def verdict(entry):
    return evaluate([entry])[0]


def crowd(target_times, others_times, others=19):
    """Return [target, others...]: every response answered the open-text questions timed."""
    answered = {question_id: OT for question_id in target_times}
    target = response(1, answered=answered, timings=target_times)
    rest = [
        response(index, answered=answered, timings=others_times)
        for index in range(2, others + 2)
    ]
    return [target, *rest]


# --- module surface -----------------------------------------------------------------


def test_module_imports_no_django_app_repository_or_service():
    source = Path(rules.__file__).read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])

    assert imported <= {"collections", "statistics"}


def test_version_flag_codes_and_bands():
    assert rules.RULES_VERSION == 1
    assert FLAG_CODES == (
        "ATTENTION_FAILED",
        "SPEEDING",
        "SIGNALS_MISSING",
        "DUPLICATE_DEVICE",
        "STRAIGHT_LINING",
    )
    assert rules.BANDS == ("CLEAN", "CHECK", "LOW")


def test_a_response_with_nothing_to_judge_is_clean_with_four_signals_not_checked():
    assert verdict(response()) == {
        "response_id": 1,
        "status": EVALUATED,
        "flags": [],
        "not_checked": [ATTENTION_FAILED, SPEEDING, DUPLICATE_DEVICE, STRAIGHT_LINING],
        "score": 100,
        "band": CLEAN,
    }


def test_a_response_without_evidence_is_before_checks():
    entry = {"response_id": 7, "respondent_id": 70, "answered": {1: MC}, "evidence": None}

    assert verdict(entry) == {
        "response_id": 7,
        "status": BEFORE_CHECKS,
        "flags": [],
        "not_checked": [],
        "score": None,
        "band": None,
    }


def test_one_verdict_per_response_in_the_input_order():
    entries = [response(3), response(1), response(2)]

    assert [item["response_id"] for item in evaluate(entries)] == [3, 1, 2]


# --- SPEEDING rule (a), the floor ---------------------------------------------------


@pytest.mark.parametrize("active_ms, flagged", [(1_999, True), (2_000, False)])
def test_floor_counts_under_2000_ms_as_fast_and_2000_as_not(active_ms, flagged):
    result = verdict(closed_response([active_ms, active_ms, 5_000, 5_000]))

    assert (SPEEDING in result["flags"]) is flagged
    assert SPEEDING not in result["not_checked"]


@pytest.mark.parametrize(
    "times, flagged",
    [
        ([1_000, 1_000, 5_000, 5_000], True),  # exactly half
        ([1_000, 5_000, 5_000, 5_000], False),  # under half
    ],
)
def test_floor_flags_at_least_half_fast(times, flagged):
    assert (SPEEDING in verdict(closed_response(times))["flags"]) is flagged


def test_floor_needs_3_timed_closed_questions():
    two = verdict(closed_response([10, 10]))
    three = verdict(closed_response([10, 10, 10]))

    assert SPEEDING in two["not_checked"]
    assert SPEEDING not in two["flags"]
    assert SPEEDING in three["flags"]


def test_floor_leaves_out_open_text_and_unanswered_or_untimed_questions():
    entry = response(
        answered={1: MC, 2: RS, 3: OT, 4: MC},
        timings={1: 10, 2: 10, 3: 10, 5: 10},  # 4 has no timing, 5 was not answered
    )

    result = verdict(entry)

    assert SPEEDING in result["not_checked"]
    assert result["flags"] == []


def test_floor_counts_attention_questions_as_closed_questions():
    # Attention questions are multiple choice or rating; the rules see only their type.
    entry = closed_response([10, 10, 10], attention_total=3, attention_failed=0)

    assert SPEEDING in verdict(entry)["flags"]


# --- SPEEDING rule (b), the relative speed index -------------------------------------


def test_rsi_waits_for_20_signals_ok_responses():
    nineteen = crowd({1: 1_000}, {1: 5_000}, others=18)
    nineteen.append(response(99, answered={1: OT}, timings={1: 5_000}, signals_ok=False))
    twenty = crowd({1: 1_000}, {1: 5_000}, others=19)

    assert SPEEDING in evaluate(nineteen)[0]["not_checked"]
    assert SPEEDING in evaluate(twenty)[0]["flags"]


@pytest.mark.parametrize("active_ms, flagged", [(2_001, False), (2_000, True)])
def test_rsi_flags_at_2_and_not_just_under(active_ms, flagged):
    # Median 4,000 ms: 4,000 / 2,000 is exactly 2.0; 4,000 / 2,001 is just under.
    result = evaluate(crowd({1: active_ms}, {1: 4_000}))[0]

    assert (SPEEDING in result["flags"]) is flagged
    assert SPEEDING not in result["not_checked"]


def test_rsi_floors_a_time_at_100_ms():
    # Question 1: 150 / max(0, 100) = 1.5; question 2: factor 1. Mean 1.25, not flagged.
    # Without the floor the first factor would be capped at 3 and the mean would be 2.0.
    result = evaluate(crowd({1: 0, 2: 5_000}, {1: 150, 2: 5_000}))[0]

    assert SPEEDING not in result["flags"]


def test_rsi_caps_a_factor_at_3():
    # Question 1: 10,000 / 100 = 100, capped at 3; question 2: 5,000 / 10,000 = 0.5.
    # Mean 1.75 with the cap, not flagged; without the cap it would be 50.25.
    result = evaluate(crowd({1: 100, 2: 10_000}, {1: 10_000, 2: 5_000}))[0]

    assert SPEEDING not in result["flags"]


def test_open_text_answers_are_outside_the_floor_but_inside_the_rsi():
    answered = {1: MC, 2: RS, 3: OT}
    fast_text = {1: 5_000, 2: 5_000, 3: 10}
    few = [response(1, answered=answered, timings=fast_text)]
    target = response(1, answered=answered, timings={1: 5_000, 2: 5_000, 3: 100})
    others = [
        response(index, answered=answered, timings={1: 5_000, 2: 5_000, 3: 60_000})
        for index in range(2, 21)
    ]

    # Two timed closed answers: the floor cannot run, and the fast text does not help it.
    assert SPEEDING in evaluate(few)[0]["not_checked"]
    # With 20 responses the text question joins the RSI: factors 1, 1, 3 give 1.67.
    assert SPEEDING not in evaluate([target, *others])[0]["flags"]
    # Two fast closed answers more push it over: factors 3, 3, 3.
    quick = response(1, answered=answered, timings={1: 100, 2: 100, 3: 100})
    assert SPEEDING in evaluate([quick, *others])[0]["flags"]


def test_rsi_medians_use_only_signals_ok_responses():
    # 20 signals_ok responses at 4,000 ms with the target at 2,000: median 4,000, RSI 2.0.
    # Ten more responses at 1 ms without signals must not pull the median down.
    entries = crowd({1: 2_000}, {1: 4_000})
    entries += [
        response(index, answered={1: OT}, timings={1: 1}, signals_ok=False)
        for index in range(100, 110)
    ]

    assert SPEEDING in evaluate(entries)[0]["flags"]


# --- SIGNALS_MISSING ------------------------------------------------------------------


def test_signals_ok_false_gives_signals_missing_and_speeding_not_checked():
    result = verdict(closed_response([10, 10, 10, 10], signals_ok=False))

    assert result["flags"] == [SIGNALS_MISSING]
    assert SPEEDING in result["not_checked"]
    assert result["score"] == 70


# --- STRAIGHT_LINING -----------------------------------------------------------------


def test_straight_lining_needs_5_ratings():
    four = verdict(response(rating_count=4, rating_all_same=True))
    five = verdict(response(rating_count=5, rating_all_same=True))

    assert STRAIGHT_LINING in four["not_checked"]
    assert STRAIGHT_LINING not in four["flags"]
    assert STRAIGHT_LINING in five["flags"]


def test_one_differing_rating_is_not_straight_lining():
    result = verdict(response(rating_count=5, rating_all_same=False))

    assert STRAIGHT_LINING not in result["flags"]
    assert STRAIGHT_LINING not in result["not_checked"]


# --- ATTENTION_FAILED ----------------------------------------------------------------


@pytest.mark.parametrize("failed, expected_score", [(0, 100), (1, 60), (2, 20), (3, 20)])
def test_attention_costs_40_per_failed_check_and_three_count_as_two(failed, expected_score):
    result = verdict(response(attention_total=3, attention_failed=failed))

    assert (ATTENTION_FAILED in result["flags"]) is (failed >= 1)
    assert ATTENTION_FAILED not in result["not_checked"]
    assert result["score"] == expected_score


# --- DUPLICATE_DEVICE ----------------------------------------------------------------


def test_two_respondents_on_one_hash_are_both_flagged():
    entries = [
        response(1, device_hash="a" * 64),
        response(2, device_hash="a" * 64),
        response(3, device_hash="b" * 64),
    ]

    flags = [item["flags"] for item in evaluate(entries)]

    assert flags == [[DUPLICATE_DEVICE], [DUPLICATE_DEVICE], []]


def test_an_empty_hash_never_matches():
    results = evaluate([response(1), response(2)])

    for result in results:
        assert DUPLICATE_DEVICE not in result["flags"]
        assert DUPLICATE_DEVICE in result["not_checked"]


# --- score and bands -----------------------------------------------------------------


@pytest.mark.parametrize(
    "code, expected",
    [
        (ATTENTION_FAILED, 60),
        (SPEEDING, 70),
        (SIGNALS_MISSING, 70),
        (DUPLICATE_DEVICE, 80),
        (STRAIGHT_LINING, 90),
    ],
)
def test_each_penalty_alone(code, expected):
    assert rules.score([code], attention_failed=1) == expected


def test_every_flag_together_scores_0():
    assert rules.score(list(FLAG_CODES), attention_failed=2) == 0


def test_score_never_goes_under_0():
    # 2 failed checks (80) and missing signals (30) give 110 points of penalty.
    result = verdict(response(attention_total=2, attention_failed=2, signals_ok=False))

    assert result["flags"] == [ATTENTION_FAILED, SIGNALS_MISSING]
    assert result["score"] == 0
    assert result["band"] == LOW


@pytest.mark.parametrize("value, expected", [(100, CLEAN), (99, CHECK), (60, CHECK), (59, LOW)])
def test_band_edges(value, expected):
    assert rules.band(value) == expected


def test_flags_are_listed_in_the_fixed_order():
    entries = [
        closed_response(
            [10, 10, 10],
            response_id=1,
            attention_total=1,
            attention_failed=1,
            rating_count=5,
            rating_all_same=True,
            device_hash="c" * 64,
        ),
        response(2, device_hash="c" * 64),
    ]

    result = evaluate(entries)[0]

    assert result["flags"] == [ATTENTION_FAILED, SPEEDING, DUPLICATE_DEVICE, STRAIGHT_LINING]
    assert result["not_checked"] == []
    assert result["score"] == 0
