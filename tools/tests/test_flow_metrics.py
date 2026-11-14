"""Tests for the pure functions of tools/flow_metrics.py, with fixed pull request JSON (prs.json)."""

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flow_metrics as fm  # noqa: E402

FIXTURE = Path(__file__).with_name("prs.json")
SINCE = date(2026, 11, 2)
UNTIL = date(2026, 11, 15)
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def prs():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def result(prs):
    return fm.compute(prs, SINCE, UNTIL, NOW, base="develop")


def test_parse_time_returns_aware_utc():
    assert fm.parse_time("2026-11-02T10:00:00Z") == datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "title, body, expected",
    [
        ("feat: x", "Closes #45.", [45]),
        ("feat: x", "Refs #15, #16, #20. Audit A-20.", [15, 16, 20]),
        ("feat: x (refs #3)", "Refs #8 and #9", [3, 8, 9]),
        ("feat: x", "closes #2\n\nREFS #2", [2]),
        ("feat: x", "See #12 and Fixes #13", []),
        ("feat: x", None, []),
    ],
)
def test_issue_refs(title, body, expected):
    assert fm.issue_refs(title, body) == expected


def test_first_commit_is_earliest_authored_date(prs):
    assert fm.first_commit(prs[0]) == datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)


def test_first_commit_without_commits_is_none():
    assert fm.first_commit({"commits": []}) is None


def test_days_rounds_to_one_decimal():
    assert fm.days(timedelta(days=2, hours=2)) == 2.1
    assert fm.days(timedelta(hours=12)) == 0.5


@pytest.mark.parametrize(
    "values, p, expected",
    [
        (list(range(1, 21)), 85, 17),
        ([1.0, 2.1, 9.0], 85, 9.0),
        ([4.0], 85, 4.0),
        ([3.0, 1.0, 2.0], 50, 2.0),
        ([], 85, None),
    ],
)
def test_percentile_nearest_rank(values, p, expected):
    assert fm.percentile_nearest_rank(values, p) == expected


def test_iso_week():
    assert fm.iso_week(date(2026, 11, 2)) == "2026-W45"
    assert fm.iso_week(date(2026, 11, 15)) == "2026-W46"


def test_weeks_in_range_lists_every_week():
    assert fm.weeks_in_range(SINCE, UNTIL) == ["2026-W45", "2026-W46"]
    assert fm.weeks_in_range(date(2026, 12, 30), date(2027, 1, 5)) == ["2026-W53", "2027-W01"]


def test_needs_commits_only_for_open_or_merged_in_range(prs):
    selected = [pr["number"] for pr in prs if fm.needs_commits(pr, SINCE, UNTIL, "develop")]
    assert selected == [10, 11, 12, 14]


def test_merged_in_range_includes_the_last_day():
    assert fm.merged_in_range({"mergedAt": "2026-11-15T23:59:59Z"}, SINCE, UNTIL)
    assert not fm.merged_in_range({"mergedAt": "2026-11-16T00:00:00Z"}, SINCE, UNTIL)
    assert not fm.merged_in_range({"mergedAt": None}, SINCE, UNTIL)


def test_merged_rows_only_in_range_and_base(result):
    assert [row["number"] for row in result["merged"]] == [10, 12, 11]
    assert [row["cycle_days"] for row in result["merged"]] == [2.1, 1.0, 9.0]
    assert result["merged"][1]["issues"] == [8, 9]


def test_issue_spans_earliest_first_commit_to_last_merge(result):
    issues = {row["issue"]: row for row in result["issues"]}
    assert sorted(issues) == [5, 7, 8, 9]
    assert issues[5]["prs"] == [10, 11]
    assert issues[5]["first_commit"] == datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    assert issues[5]["merged"] == datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
    assert issues[5]["cycle_days"] == 10.1
    assert issues[7]["cycle_days"] == 9.0


def test_throughput_per_iso_week(result):
    assert result["throughput"] == {"2026-W45": 1, "2026-W46": 2}


def test_wip_and_age_of_open_pull_requests(result):
    assert result["wip"] == 1
    assert [(row["number"], row["age_days"]) for row in result["open"]] == [(14, 1.5)]


def test_service_level(result):
    assert result["within_7_days"] == (2, 3)
    assert result["p85"] == 9.0


def test_service_level_with_nothing_merged():
    empty = fm.compute([], SINCE, UNTIL, NOW, base="develop")
    assert empty["within_7_days"] == (0, 0)
    assert empty["p85"] is None
    assert empty["throughput"] == {"2026-W45": 0, "2026-W46": 0}


def test_render_markdown_contains_headline_values(result):
    text = fm.render_markdown(result, SINCE, UNTIL, "develop", "abc1234", NOW)
    assert "2026-11-02 to 2026-11-15" in text
    assert "abc1234" in text
    assert "| 12 | docs: two issues \\| one PR | #8, #9 |" in text
    assert "2 of 3 (66.7%)" in text
    assert "9.0 days" in text
    assert "project" in text
