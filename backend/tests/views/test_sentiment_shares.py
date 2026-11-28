"""TASK-50 (board W-05b): bar widths by the largest remainder; labels keep the ordinary rounding.

No database: _sentiment_shares works on a plain counts dict.
"""

import pytest

from apps.analysis.views import _sentiment_shares


def shares_of(positive, neutral, negative):
    return _sentiment_shares(
        {
            "analysed": positive + neutral + negative,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
        }
    )


def widths(positive, neutral, negative):
    return [share["width"] for share in shares_of(positive, neutral, negative)]


@pytest.mark.parametrize(
    "counts, expected",
    [
        ((1, 1, 1), [34, 33, 33]),
        ((2, 2, 3), [29, 28, 43]),
        ((3, 1, 1), [60, 20, 20]),
        ((0, 5, 0), [0, 100, 0]),
        ((0, 0, 0), [0, 0, 0]),
    ],
)
def test_the_examples(counts, expected):
    assert widths(*counts) == expected


def test_every_split_up_to_twelve_sums_to_100_within_1_of_the_share():
    for total in range(1, 13):
        for positive in range(total + 1):
            for neutral in range(total - positive + 1):
                counts = (positive, neutral, total - positive - neutral)
                result = widths(*counts)
                assert sum(result) == 100, counts
                for count, width in zip(counts, result):
                    assert abs(width - count * 100 / total) < 1, counts


def test_the_keys_and_labels_stay_as_before():
    shares = shares_of(1, 1, 1)

    assert [set(share) for share in shares] == [{"key", "name", "count", "label", "width"}] * 3
    assert [share["key"] for share in shares] == ["positive", "neutral", "negative"]
    assert [share["name"] for share in shares] == ["Positive", "Neutral", "Negative"]
    assert [share["count"] for share in shares] == [1, 1, 1]
    assert [share["label"] for share in shares] == ["33%", "33%", "33%"]
