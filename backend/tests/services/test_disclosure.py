"""P-19: counts of 1 to 4 people are never shown as a number."""

import pytest

from services.disclosure import MIN_GROUP_SIZE, band


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, {"state": "none", "count": 0}),
        (1, {"state": "few", "count": None}),
        (4, {"state": "few", "count": None}),
        (5, {"state": "exact", "count": 5}),
        (6, {"state": "exact", "count": 6}),
    ],
)
def test_band_hides_counts_from_one_to_four(count, expected):
    assert band(count) == expected


def test_min_group_size_is_five():
    assert MIN_GROUP_SIZE == 5
