"""P-19: counts of 1 to 4 people are never shown as a number."""

import pytest

from services.disclosure import MIN_GROUP_SIZE, band, pool_groups, results_open


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


@pytest.mark.parametrize(
    ("response_count", "expected"),
    [(0, False), (4, False), (5, True), (6, True)],
)
def test_results_open_from_five_responses(response_count, expected):
    """P-20: a survey's results stay closed until it has MIN_GROUP_SIZE responses."""
    assert results_open(response_count) is expected


# P-15, DESIGN-INC2 3.6: groups under MIN_GROUP_SIZE are pooled, and the pool itself is
# never 1 to 4.


def test_pool_groups_pools_small_groups_that_reach_five_together():
    result = pool_groups({"Damascus": 12, "Aleppo": 7, "Homs": 3, "Hama": 2})

    assert result == {"shown": ["Damascus", "Aleppo"], "pooled": ["Homs", "Hama"], "enough": True}


def test_pool_groups_moves_the_smallest_shown_group_while_the_pool_is_under_five():
    result = pool_groups({"Damascus": 12, "Aleppo": 7, "Homs": 3})

    assert result == {"shown": ["Damascus"], "pooled": ["Aleppo", "Homs"], "enough": True}


def test_pool_groups_is_not_enough_when_only_the_pool_is_left():
    result = pool_groups({"Damascus": 6, "Homs": 2})

    assert result == {"shown": [], "pooled": ["Damascus", "Homs"], "enough": False}


def test_pool_groups_pools_four_and_shows_five():
    result = pool_groups({"Aleppo": 5, "Damascus": 5, "Homs": 4, "Hama": 1})

    assert result["shown"] == ["Aleppo", "Damascus"]
    assert result["pooled"] == ["Homs", "Hama"]
    assert result["enough"] is True


def test_pool_groups_moves_the_group_listed_last_between_equal_counts():
    result = pool_groups({"Damascus": 20, "Aleppo": 6, "Hama": 6, "Homs": 2})

    assert result["shown"] == ["Damascus", "Aleppo"]
    assert result["pooled"] == ["Hama", "Homs"]


def test_pool_groups_orders_shown_by_count_then_label():
    result = pool_groups({"Homs": 9, "Aleppo": 9, "Damascus": 15})

    assert result == {"shown": ["Damascus", "Aleppo", "Homs"], "pooled": [], "enough": True}


def test_pool_groups_ignores_zero_counts():
    result = pool_groups({"Damascus": 8, "Aleppo": 6, "Homs": 0})

    assert result == {"shown": ["Damascus", "Aleppo"], "pooled": [], "enough": True}


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({"Damascus": 10}, {"shown": ["Damascus"], "pooled": [], "enough": False}),
        ({"Damascus": 3}, {"shown": [], "pooled": ["Damascus"], "enough": False}),
    ],
)
def test_pool_groups_one_group_alone_is_not_enough(counts, expected):
    assert pool_groups(counts) == expected


def test_pool_groups_with_no_groups():
    assert pool_groups({}) == {"shown": [], "pooled": [], "enough": False}
