# Flow metrics — 2026-11-16 to 2026-11-28

- Range: 2026-11-16 to 2026-11-28 inclusive (UTC), pull requests into `develop`.
- Run at commit `4e7ca64` on 2026-11-28 15:57 UTC by `tools/flow_metrics.py`.
- Times in UTC. Durations in days with one decimal. First commit = earliest `authoredDate` on the branch.

## Headline

| Metric | Value |
|---|---|
| WIP (open pull requests now) | 0 |
| Throughput (merged in range) | 33 |
| Cycle time within 7 days | 33 of 33 (100.0%) |
| 85th percentile of cycle time (nearest rank) | 0.4 days |

## Reading the numbers

- Each task branch in this range starts with an empty start commit (planning/KANBAN.md), made when the coding of the
  task begins. A pull request's cycle time therefore runs from the start of coding to the merge. The design, its board
  and the task brief come before the branch and are not in these numbers. All 33 merged pull requests have a
  `chore: start TASK-` commit as their first commit, so none of them measures review time only.
- Issue level: 16 issues have a merged pull request in the range; 16 of 16 (100.0%) have an issue cycle time within
  7 days; the 85th percentile of issue cycle time (nearest rank) is 2.0 days.
- Pull requests 91, 103 and 104 reference no issue. They are not in the issue table.
- The release pull request #109 went into main, not develop, so it is not counted.
- Service level: The SLE of Increment 1 was 85% of items within 7 days. The issue-level share of 100.0% meets it.
  Proposed for Increment 3, for the team's decision at the review: 85% of items within 7 days.

## Merged pull requests (cycle time)

| PR | Title | Issues | First commit | Merged | Cycle time (days) |
|---|---|---|---|---|---|
| 74 | chore: T-9 remove the dormant Celery path; the stack runs run_analysis_worker (TASK-30) | #72 | 2026-11-16 15:18 | 2026-11-18 12:12 | 1.9 |
| 75 | fix: T-9 the app's submit uses the default timeout (TASK-31) | #72 | 2026-11-18 12:30 | 2026-11-18 13:11 | 0.0 |
| 76 | feat: FR-03 criteria lists and one matching rule (TASK-33) | #17 | 2026-11-18 13:28 | 2026-11-18 14:05 | 0.0 |
| 77 | feat: FR-03 reach count, its privacy band and synthetic respondents (TASK-34) | #17 | 2026-11-18 14:22 | 2026-11-18 15:17 | 0.0 |
| 78 | feat: FR-03 targeting page with live reach and a publish confirmation (TASK-35) | #17 | 2026-11-18 17:51 | 2026-11-18 18:16 | 0.0 |
| 79 | feat: results open at 5 responses (P-20, TASK-38) | #23 | 2026-11-18 18:21 | 2026-11-18 18:32 | 0.0 |
| 80 | feat: W-05a sentiment panel with reasons, retry and the due-time hint (TASK-36) | #72 | 2026-11-18 18:36 | 2026-11-18 18:58 | 0.0 |
| 81 | feat: T-2 results, M4 chosen by the NFR-07 rule (TASK-37) | #36 | 2026-11-18 19:01 | 2026-11-19 12:27 | 0.7 |
| 82 | feat: FR-05 worker analyses with M4 locally, weights checked (TASK-39) | #19 | 2026-11-19 15:17 | 2026-11-19 16:00 | 0.0 |
| 83 | chore: smoke runs the worker command; model files checked against a manifest (TASK-40) | #19, #72 | 2026-11-19 16:57 | 2026-11-19 17:13 | 0.0 |
| 84 | feat: FR-04 evidence at submit, attention questions, response snapshot; respondent web pages retired (TASK-41) | #18 | 2026-11-19 17:22 | 2026-11-19 17:52 | 0.0 |
| 85 | feat: FR-04 quality rules, score and include or exclude; analytics count included responses (TASK-42) | #18 | 2026-11-19 17:54 | 2026-11-19 22:23 | 0.2 |
| 86 | feat: FR-04 attention option on the question form, response quality panel and bulk include or exclude (TASK-43) | #18 | 2026-11-19 22:40 | 2026-11-19 23:26 | 0.0 |
| 87 | feat: FR-04 app sends a start mark, active time per question and an install ID; A-04 notice (TASK-44) | #18 | 2026-11-19 23:42 | 2026-11-20 00:12 | 0.0 |
| 88 | feat: FR-04 labelled simulation of response styles (TASK-45) | #18 | 2026-11-20 00:21 | 2026-11-20 11:02 | 0.4 |
| 89 | docs: FR-04 class, ER and UC-04 sequence diagrams at f3c96d4; quality rules activity diagram (TASK-46) | #18 | 2026-11-20 11:18 | 2026-11-20 11:56 | 0.0 |
| 90 | docs: PNG exports of the Increment 2 diagrams (TASK-46B) | #18 | 2026-11-20 11:58 | 2026-11-20 12:09 | 0.0 |
| 91 | fix: question form drops options left over from another type (TASK-47) | - | 2026-11-20 12:20 | 2026-11-20 12:52 | 0.0 |
| 92 | feat: FR-05 sentiment per question and per group with small groups pooled (TASK-48) | #19 | 2026-11-20 12:54 | 2026-11-20 15:56 | 0.1 |
| 93 | feat: FR-07 and FR-09 responses one by one under a number, include or exclude one (TASK-49) | #21, #23 | 2026-11-20 16:21 | 2026-11-20 17:18 | 0.0 |
| 94 | fix: W-05b state 7 line, bar widths and message boxes; response pages get a date only (TASK-50) | #19, #21, #23 | 2026-11-20 17:40 | 2026-11-20 18:01 | 0.0 |
| 95 | feat: FR-14 export the included responses and their quality verdicts to CSV and Excel (TASK-51) | #28 | 2026-11-20 18:12 | 2026-11-20 18:44 | 0.0 |
| 96 | feat: FR-16 shuffled order of questions and options, fixed per respondent (TASK-52) | #30 | 2026-11-20 18:46 | 2026-11-20 19:08 | 0.0 |
| 97 | feat: FR-08 survey list ranked by shared interests, with expected time, search and filters (TASK-53) | #22 | 2026-11-20 19:14 | 2026-11-20 19:41 | 0.0 |
| 98 | feat: FR-12 survey review, the admin approves or rejects with a reason before publishing (TASK-54) | #26 | 2026-11-20 19:45 | 2026-11-20 20:29 | 0.0 |
| 99 | feat: FR-11 survey lifecycle, opening and closing dates, a response limit, pause and resume (TASK-55) | #25 | 2026-11-20 20:40 | 2026-11-21 06:29 | 0.4 |
| 100 | feat: FR-13 advanced analytics, one filter by group, comparison tables, responses over time (TASK-56) | #27 | 2026-11-21 13:51 | 2026-11-21 14:57 | 0.0 |
| 101 | feat: FR-15 Part A, role permissions proven in the service layer and the submit endpoint throttled (TASK-57) | #29 | 2026-11-21 15:18 | 2026-11-21 15:47 | 0.0 |
| 102 | feat: FR-15 Part B, email confirmation before the first log-in and password recovery on the website (TASK-58) | #29 | 2026-11-21 15:54 | 2026-11-27 13:46 | 5.9 |
| 103 | docs: Increment 2 diagrams at 59f1957, class and ER redrawn, survey and sentiment state machines, component and sentiment data-flow diagrams (TASK-59) | - | 2026-11-27 14:21 | 2026-11-27 14:26 | 0.0 |
| 104 | docs: Increment 2 sequence diagrams at 59f1957, UC-01, UC-03, UC-10, UC-12, UC-13, UC-14 new and UC-04 redrawn (TASK-60) | - | 2026-11-27 14:55 | 2026-11-27 14:59 | 0.0 |
| 106 | fix: serve Bootstrap, Bootstrap Icons, the fonts and Chart.js from static files so the website works offline (TASK-62) | #105 | 2026-11-28 13:55 | 2026-11-28 14:15 | 0.0 |
| 108 | docs: Graduation 1 report diagrams, 47 PlantUML sources with PNGs and three charts (TASK-61) | #107 | 2026-11-28 14:29 | 2026-11-28 15:00 | 0.0 |

## Issues (first commit of the earliest pull request to merge of the last)

| Issue | Pull requests | First commit | Last merge | Cycle time (days) |
|---|---|---|---|---|
| #17 | 76, 77, 78 | 2026-11-18 13:28 | 2026-11-18 18:16 | 0.2 |
| #18 | 84, 85, 86, 87, 88, 89, 90 | 2026-11-19 17:22 | 2026-11-20 12:09 | 0.8 |
| #19 | 82, 83, 92, 94 | 2026-11-19 15:17 | 2026-11-20 18:01 | 1.1 |
| #21 | 93, 94 | 2026-11-20 16:21 | 2026-11-20 18:01 | 0.1 |
| #22 | 97 | 2026-11-20 19:14 | 2026-11-20 19:41 | 0.0 |
| #23 | 79, 93, 94 | 2026-11-18 18:21 | 2026-11-20 18:01 | 2.0 |
| #25 | 99 | 2026-11-20 20:40 | 2026-11-21 06:29 | 0.4 |
| #26 | 98 | 2026-11-20 19:45 | 2026-11-20 20:29 | 0.0 |
| #27 | 100 | 2026-11-21 13:51 | 2026-11-21 14:57 | 0.0 |
| #28 | 95 | 2026-11-20 18:12 | 2026-11-20 18:44 | 0.0 |
| #29 | 101, 102 | 2026-11-21 15:18 | 2026-11-27 13:46 | 5.9 |
| #30 | 96 | 2026-11-20 18:46 | 2026-11-20 19:08 | 0.0 |
| #36 | 81 | 2026-11-18 19:01 | 2026-11-19 12:27 | 0.7 |
| #72 | 74, 75, 80, 83 | 2026-11-16 15:18 | 2026-11-19 17:13 | 3.1 |
| #105 | 106 | 2026-11-28 13:55 | 2026-11-28 14:15 | 0.0 |
| #107 | 108 | 2026-11-28 14:29 | 2026-11-28 15:00 | 0.0 |

## Throughput per ISO week

| Week | Merged pull requests |
|---|---|
| 2026-W47 | 28 |
| 2026-W48 | 5 |

## WIP and work item age (open pull requests now: 0)

| PR | Title | Issues | First commit | Age (days) |
|---|---|---|---|---|

## Service level

- Cycle times within 7 days: 33 of 33 (100.0%).
- 85th percentile of the cycle times (nearest rank): 0.4 days.

## Not measured

- In Progress (a branch without a pull request) is not counted in WIP: reading the board needs the `project` scope on the gh token.
