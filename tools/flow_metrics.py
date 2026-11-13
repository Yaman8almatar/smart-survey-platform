"""Flow metrics (T-5) from the repository's pull requests, as defined in planning/KANBAN.md.

An item's branch is one pull request into the base branch.
- Cycle time: merge time minus the first commit on the branch, for pull requests merged in the range.
- Throughput: pull requests merged into the base branch per ISO week in the range.
- Work item age: now minus the first commit, for pull requests still open.
- WIP: open pull requests into the base branch now (the Review state).

Usage (from the repository root):
    .venv/Scripts/python.exe tools/flow_metrics.py --since 2026-11-02 --until 2026-11-15 \
        --out planning/flow-metrics-increment1.md

Standard library only; GitHub data comes from the gh CLI (read-only `gh pr list`).
"""

import argparse
import json
import math
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

SLE_DAYS = 7.0
SLE_PERCENTILE = 85
GH_FIELDS = "number,title,body,state,createdAt,mergedAt,headRefName,baseRefName"
GH_LIMIT = 1000
REF_PATTERN = re.compile(r"\b(?:refs|closes)\b:?\s*(#\d+(?:(?:\s*,\s*|\s+and\s+)#\d+)*)", re.IGNORECASE)


# ---------------------------------------------------------------- pure functions


def parse_time(value):
    """ISO 8601 timestamp from GitHub ("...Z") -> timezone-aware UTC datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def issue_refs(title, body):
    """Issue numbers named by "Refs #N" or "Closes #N" (also "Refs #1, #2" and "Refs #1 and #2")."""
    text = f"{title or ''}\n{body or ''}"
    numbers = set()
    for match in REF_PATTERN.finditer(text):
        numbers.update(int(n) for n in re.findall(r"#(\d+)", match.group(1)))
    return sorted(numbers)


def first_commit(pr):
    """Earliest authoredDate among the pull request's commits, or None without commits."""
    dates = [parse_time(c["authoredDate"]) for c in pr.get("commits") or [] if c.get("authoredDate")]
    return min(dates) if dates else None


def days(delta):
    """timedelta -> days with one decimal."""
    return round(delta.total_seconds() / 86400, 1)


def percentile_nearest_rank(values, p):
    """Nearest-rank percentile: the value at rank ceil(p/100 * n) of the sorted values; None if empty."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def iso_week(day):
    """date or datetime -> ISO week label such as 2026-W45."""
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def weeks_in_range(since, until):
    """Every ISO week that overlaps the inclusive date range, in order."""
    weeks = []
    day = since
    while day <= until:
        label = iso_week(day)
        if label not in weeks:
            weeks.append(label)
        day += timedelta(days=1)
    return weeks


def range_bounds(since, until):
    """Inclusive date range -> [since 00:00 UTC, until+1 00:00 UTC)."""
    start = datetime.combine(since, time.min, tzinfo=timezone.utc)
    end = datetime.combine(until + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


def merged_in_range(pr, since, until):
    """True if the pull request was merged within the inclusive date range (UTC)."""
    if not pr.get("mergedAt"):
        return False
    start, end = range_bounds(since, until)
    return start <= parse_time(pr["mergedAt"]) < end


def needs_commits(pr, since, until, base):
    """True if the metrics use this pull request's commits: into `base` and open now or merged in range."""
    if pr.get("baseRefName") != base:
        return False
    return pr.get("state") == "OPEN" or merged_in_range(pr, since, until)


def compute(prs, since, until, now, base="develop"):
    """All flow metrics for pull requests into `base`, merged in [since, until] or open now."""
    into_base = [pr for pr in prs if pr.get("baseRefName") == base]

    merged = []
    for pr in into_base:
        first = first_commit(pr)
        if not merged_in_range(pr, since, until) or first is None:
            continue
        merged_at = parse_time(pr["mergedAt"])
        merged.append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "issues": issue_refs(pr["title"], pr.get("body")),
                "first_commit": first,
                "merged": merged_at,
                "cycle_days": days(merged_at - first),
            }
        )
    merged.sort(key=lambda row: row["merged"])

    by_issue = {}
    for row in merged:
        for issue in row["issues"]:
            by_issue.setdefault(issue, []).append(row)
    issues = []
    for issue in sorted(by_issue):
        rows = by_issue[issue]
        first = min(r["first_commit"] for r in rows)
        last = max(r["merged"] for r in rows)
        issues.append(
            {
                "issue": issue,
                "prs": sorted(r["number"] for r in rows),
                "first_commit": first,
                "merged": last,
                "cycle_days": days(last - first),
            }
        )

    throughput = {week: 0 for week in weeks_in_range(since, until)}
    for row in merged:
        throughput[iso_week(row["merged"])] += 1

    open_rows = []
    for pr in into_base:
        if pr.get("state") != "OPEN":
            continue
        first = first_commit(pr)
        open_rows.append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "issues": issue_refs(pr["title"], pr.get("body")),
                "first_commit": first,
                "age_days": days(now - first) if first else None,
            }
        )
    open_rows.sort(key=lambda row: row["number"])

    cycles = [row["cycle_days"] for row in merged]
    return {
        "merged": merged,
        "issues": issues,
        "throughput": throughput,
        "open": open_rows,
        "wip": len(open_rows),
        "within_7_days": (sum(1 for c in cycles if c <= SLE_DAYS), len(cycles)),
        "p85": percentile_nearest_rank(cycles, SLE_PERCENTILE),
    }


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def _when(moment):
    return moment.strftime("%Y-%m-%d %H:%M") if moment else "-"


def _refs(numbers):
    return ", ".join(f"#{n}" for n in numbers) if numbers else "-"


def render_markdown(result, since, until, base, commit, now):
    """Report text: tables and numbers only."""
    within, total = result["within_7_days"]
    share = f"{within} of {total} ({within / total * 100:.1f}%)" if total else "0 of 0 (no merged pull requests)"
    p85 = f"{result['p85']:.1f} days" if result["p85"] is not None else "- (no merged pull requests)"
    lines = [
        f"# Flow metrics — {since.isoformat()} to {until.isoformat()}",
        "",
        f"- Range: {since.isoformat()} to {until.isoformat()} inclusive (UTC), pull requests into `{base}`.",
        f"- Run at commit `{commit}` on {_when(now)} UTC by `tools/flow_metrics.py`.",
        "- Times in UTC. Durations in days with one decimal. First commit = earliest `authoredDate` on the branch.",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| WIP (open pull requests now) | {result['wip']} |",
        f"| Throughput (merged in range) | {total} |",
        f"| Cycle time within {SLE_DAYS:.0f} days | {share} |",
        f"| {SLE_PERCENTILE}th percentile of cycle time (nearest rank) | {p85} |",
        "",
        "## Merged pull requests (cycle time)",
        "",
        "| PR | Title | Issues | First commit | Merged | Cycle time (days) |",
        "|---|---|---|---|---|---|",
    ]
    for row in result["merged"]:
        lines.append(
            f"| {row['number']} | {_cell(row['title'])} | {_refs(row['issues'])} | "
            f"{_when(row['first_commit'])} | {_when(row['merged'])} | {row['cycle_days']:.1f} |"
        )
    lines += [
        "",
        "## Issues (first commit of the earliest pull request to merge of the last)",
        "",
        "| Issue | Pull requests | First commit | Last merge | Cycle time (days) |",
        "|---|---|---|---|---|",
    ]
    for row in result["issues"]:
        prs = ", ".join(str(n) for n in row["prs"])
        lines.append(
            f"| #{row['issue']} | {prs} | {_when(row['first_commit'])} | {_when(row['merged'])} | "
            f"{row['cycle_days']:.1f} |"
        )
    lines += ["", "## Throughput per ISO week", "", "| Week | Merged pull requests |", "|---|---|"]
    for week, count in result["throughput"].items():
        lines.append(f"| {week} | {count} |")
    lines += [
        "",
        f"## WIP and work item age (open pull requests now: {result['wip']})",
        "",
        "| PR | Title | Issues | First commit | Age (days) |",
        "|---|---|---|---|---|",
    ]
    for row in result["open"]:
        age = f"{row['age_days']:.1f}" if row["age_days"] is not None else "-"
        lines.append(
            f"| {row['number']} | {_cell(row['title'])} | {_refs(row['issues'])} | "
            f"{_when(row['first_commit'])} | {age} |"
        )
    lines += [
        "",
        "## Service level",
        "",
        f"- Cycle times within {SLE_DAYS:.0f} days: {share}.",
        f"- {SLE_PERCENTILE}th percentile of the cycle times (nearest rank): {p85}.",
        "",
        "## Not measured",
        "",
        "- In Progress (a branch without a pull request) is not counted in WIP: reading the board needs the "
        "`project` scope on the gh token.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- gh and git calls


def _run(command):
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit(f"{' '.join(command[:3])} failed: {completed.stderr.strip()}")
    return completed.stdout


def fetch_prs(base, since, until):
    """Pull requests into `base` (any state), with commits for those the metrics use.

    `gh pr list --json commits` exceeds GitHub's GraphQL node limit (100 pull requests x 100 commits x 100
    authors per page), so the list is read without commits and `gh pr view` reads them per pull request.
    """
    output = _run(
        ["gh", "pr", "list", "--base", base, "--state", "all", "--limit", str(GH_LIMIT), "--json", GH_FIELDS]
    )
    prs = json.loads(output)
    if len(prs) >= GH_LIMIT:
        raise SystemExit(f"gh returned {GH_LIMIT} pull requests, the limit; older ones would be missing.")
    for pr in prs:
        if needs_commits(pr, since, until, base):
            view = _run(["gh", "pr", "view", str(pr["number"]), "--json", "commits"])
            pr["commits"] = json.loads(view)["commits"]
    return prs


def git_head():
    return _run(["git", "rev-parse", "--short", "HEAD"]).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print the four flow metrics (planning/KANBAN.md) for a date range.")
    parser.add_argument("--since", required=True, type=date.fromisoformat, help="first day, YYYY-MM-DD (UTC)")
    parser.add_argument("--until", required=True, type=date.fromisoformat, help="last day, YYYY-MM-DD (UTC, inclusive)")
    parser.add_argument("--base", default="develop", help="base branch of the pull requests (default: develop)")
    parser.add_argument("--out", type=Path, help="also write the Markdown report to this file")
    args = parser.parse_args(argv)
    if args.until < args.since:
        parser.error("--until is before --since")

    now = datetime.now(timezone.utc)
    prs = fetch_prs(args.base, args.since, args.until)
    result = compute(prs, args.since, args.until, now, base=args.base)
    text = render_markdown(result, args.since, args.until, args.base, git_head(), now)

    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
