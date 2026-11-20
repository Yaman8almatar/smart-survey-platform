from services.expected_time import MIN_VALID_RESPONSES, expected_minutes

NO_QUESTIONS = {"MULTIPLE_CHOICE": 0, "RATING_SCALE": 0, "OPEN_TEXT": 0}


def test_min_valid_responses_is_the_rsi_bar():
    assert MIN_VALID_RESPONSES == 20


def test_estimate_sums_seconds_per_type_and_rounds_up():
    # 10 + 8 + 40 = 58 seconds.
    assert expected_minutes({"MULTIPLE_CHOICE": 1, "RATING_SCALE": 1, "OPEN_TEXT": 1}, []) == 1
    # 7 * 10 = 70 seconds.
    assert expected_minutes({"MULTIPLE_CHOICE": 7, "RATING_SCALE": 0, "OPEN_TEXT": 0}, []) == 2


def test_no_question_gives_one_minute():
    assert expected_minutes(NO_QUESTIONS, []) == 1
    assert expected_minutes({}, []) == 1


def test_nineteen_valid_values_use_the_estimate():
    counts = {"MULTIPLE_CHOICE": 1, "RATING_SCALE": 0, "OPEN_TEXT": 0}

    assert expected_minutes(counts, [600_000] * (MIN_VALID_RESPONSES - 1)) == 1


def test_twenty_valid_values_use_the_median():
    counts = {"MULTIPLE_CHOICE": 1, "RATING_SCALE": 0, "OPEN_TEXT": 0}

    assert expected_minutes(counts, [600_000] * MIN_VALID_RESPONSES) == 10


def test_median_of_twenty_values_rounds_up():
    assert expected_minutes(NO_QUESTIONS, [125_000] * 20) == 3


def test_median_just_over_a_minute_rounds_up_to_two():
    assert expected_minutes(NO_QUESTIONS, [60_001] * 20) == 2


def test_median_is_the_middle_not_the_mean():
    values = [60_000] * 11 + [3_600_000] * 9

    assert expected_minutes(NO_QUESTIONS, values) == 1
