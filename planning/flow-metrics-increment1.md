# Flow metrics — 2026-11-02 to 2026-11-15

- Range: 2026-11-02 to 2026-11-15 inclusive (UTC), pull requests into `develop`.
- Run at commit `f142586` on 2026-11-13 15:41 UTC by `tools/flow_metrics.py`.
- Times in UTC. Durations in days with one decimal. First commit = earliest `authoredDate` on the branch.

## Headline

| Metric | Value |
|---|---|
| WIP (open pull requests now) | 0 |
| Throughput (merged in range) | 19 |
| Cycle time within 7 days | 18 of 19 (94.7%) |
| 85th percentile of cycle time (nearest rank) | 0.6 days |

## Merged pull requests (cycle time)

| PR | Title | Issues | First commit | Merged | Cycle time (days) |
|---|---|---|---|---|---|
| 47 | chore: merge main documents back into develop | - | 2026-10-29 12:31 | 2026-11-05 18:01 | 7.2 |
| 50 | chore: split demo and production compose files (TASK-15 Part 2) | - | 2026-11-05 21:52 | 2026-11-06 14:13 | 0.7 |
| 51 | fix: scoped throttling for auth endpoints (TASK-15 Part 3) | #38 | 2026-11-05 23:33 | 2026-11-06 14:32 | 0.6 |
| 52 | fix: map only named integrity constraints on duplicate submit (TASK-15 Part 4) | #35 | 2026-11-06 15:14 | 2026-11-06 15:48 | 0.0 |
| 53 | chore: health service, cleanup and missing tests (TASK-15 Part 5) | #48 | 2026-11-06 16:26 | 2026-11-06 16:59 | 0.0 |
| 54 | fix(mobile): logout revokes the refresh token on the server (TASK-15 Part 6) | - | 2026-11-06 17:39 | 2026-11-06 18:44 | 0.0 |
| 55 | chore: upgrade to Django 5.2 LTS (TASK-15 Part 7) | #49 | 2026-11-06 20:13 | 2026-11-06 20:58 | 0.0 |
| 56 | feat: FR-02 profile lists, completion and options endpoint (TASK-16 Part 1) | #16 | 2026-11-07 15:26 | 2026-11-07 15:42 | 0.0 |
| 57 | style: design foundation v2 for the app (TASK-17 Part B) | - | 2026-11-07 17:06 | 2026-11-07 17:29 | 0.0 |
| 58 | feat: FR-02 profile screen in the app (TASK-16 Part 2) | #16 | 2026-11-07 18:59 | 2026-11-07 19:44 | 0.0 |
| 59 | ci: pin Flutter in Flutter CI to the laptop version (TASK-18) | - | 2026-11-07 20:11 | 2026-11-07 20:16 | 0.0 |
| 60 | style: design foundation v2 for the web (TASK-17 Part A) | - | 2026-11-08 13:47 | 2026-11-08 13:57 | 0.0 |
| 62 | feat: FR-01 answer flow in the app (TASK-19) | #15, #20 | 2026-11-08 16:28 | 2026-11-08 16:57 | 0.0 |
| 63 | feat: FR-06 response drafts API (TASK-20 Part 1) | #20 | 2026-11-08 18:25 | 2026-11-08 18:32 | 0.0 |
| 64 | feat: FR-06 drafts and resume in the app (TASK-20 Part 2) | #20 | 2026-11-08 18:53 | 2026-11-08 18:58 | 0.0 |
| 65 | feat: FR-01 answered surveys screen in the app (TASK-23) | #15 | 2026-11-13 12:06 | 2026-11-13 12:21 | 0.0 |
| 66 | fix: web colour tokens, sentence case and visible sentiment failure (TASK-24) | #61 | 2026-11-13 14:05 | 2026-11-13 14:18 | 0.0 |
| 67 | fix: sentence-case question type labels and answer direction (TASK-24B) | #61 | 2026-11-13 14:30 | 2026-11-13 14:47 | 0.0 |
| 68 | docs: Increment 1 class, ER and sequence diagrams (TASK-25) | #15, #16, #20 | 2026-11-13 15:00 | 2026-11-13 15:39 | 0.0 |

## Issues (first commit of the earliest pull request to merge of the last)

| Issue | Pull requests | First commit | Last merge | Cycle time (days) |
|---|---|---|---|---|
| #15 | 62, 65, 68 | 2026-11-08 16:28 | 2026-11-13 15:39 | 5.0 |
| #16 | 56, 58, 68 | 2026-11-07 15:26 | 2026-11-13 15:39 | 6.0 |
| #20 | 62, 63, 64, 68 | 2026-11-08 16:28 | 2026-11-13 15:39 | 5.0 |
| #35 | 52 | 2026-11-06 15:14 | 2026-11-06 15:48 | 0.0 |
| #38 | 51 | 2026-11-05 23:33 | 2026-11-06 14:32 | 0.6 |
| #48 | 53 | 2026-11-06 16:26 | 2026-11-06 16:59 | 0.0 |
| #49 | 55 | 2026-11-06 20:13 | 2026-11-06 20:58 | 0.0 |
| #61 | 66, 67 | 2026-11-13 14:05 | 2026-11-13 14:47 | 0.0 |

## Throughput per ISO week

| Week | Merged pull requests |
|---|---|
| 2026-W45 | 15 |
| 2026-W46 | 4 |

## WIP and work item age (open pull requests now: 0)

| PR | Title | Issues | First commit | Age (days) |
|---|---|---|---|---|

## Service level

- Cycle times within 7 days: 18 of 19 (94.7%).
- 85th percentile of the cycle times (nearest rank): 0.6 days.

## Not measured

- In Progress (a branch without a pull request) is not counted in WIP: reading the board needs the `project` scope on the gh token.
