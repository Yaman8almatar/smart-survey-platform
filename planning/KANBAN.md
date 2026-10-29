# Kanban workflow — Smart Survey Platform, Graduation 1

The team manages its work with Kanban as defined in [The Kanban Guide](https://kanbanguides.org/the-kanban-guide/)
(May 2025), combined with Agile Modeling for design. This file is the team's **Definition of Workflow**; the board
in [GitHub Projects](https://github.com/users/Yaman8almatar/projects/1) shows it. Change this file and the board
together, and only after the team agrees (usually at the two-week review).

## Why Kanban

The three members work in a hybrid pattern: some days together, some days each from home. Kanban prescribes no
roles, events or location. Its minimum is an explicit workflow, explicit control of work in progress (WIP) and four
flow metrics, which the team can apply and show from its GitHub records. Scrum, the first choice, was replaced
because its Daily Scrum and separate roles did not fit this pattern.

## Definition of Workflow

| Element | Policy |
|---|---|
| Work item | One backlog issue: a requirement FR-01..FR-20 (user story) or a technical item T-1..T-5. |
| Started | When the item's branch is created (the card moves to **In Progress**). |
| Finished | When its pull request is merged into `develop` (the card moves to **Done**). |
| States | Backlog → Ready → In Progress → Review → Done → Released |
| WIP control | **In Progress ≤ 3** (one item per member). **Review ≤ 2**. Shown as column limits on the board view. GitHub highlights a column above its limit but does not block it, so the limit is a team rule. |
| Service level expectation | Initial estimate: 85% of items finish within 7 days. Recalculated from the measured cycle times after the first two weeks. |

## Policies per state

| State | Enter when | Leave when |
|---|---|---|
| Backlog | The item exists as an issue with a MoSCoW priority. | It has acceptance criteria and is chosen at a replenishment. |
| Ready | Acceptance criteria are written; the order is Must, then Should, then Could. | A member below the WIP limit pulls it and creates its branch. |
| In Progress | Branch created from an up-to-date `develop`; the issue is assigned to the member. | A pull request to `develop` is open and references the issue. |
| Review | Pull request open, CI running. | A member who did not write the change approved it and CI is green. |
| Done | Squash-merged into `develop`; Definition of Done met. | `develop` is released to `main` and tagged. |
| Released | The release pull request is merged into `main` and tagged; GitHub closes the issue. | — |

**Definition of Done:** tests green in CI; the pull request reviewed by another member; affected diagrams
updated; the item's report section and its three defence questions written.

**Blocked items:** add the label `blocked`, write the reason in a comment and mention a teammate; the teammate
answers within 24 hours.

## Cadence (team choice)

- **Weekly replenishment (10 minutes, on a joint day):** move the next items from Backlog to Ready and check
  their acceptance criteria.
- **Remote days:** each member writes a three-line check-in in the team chat: done, next, blocked.
- **Every two weeks (end of an Increment):** review with the supervisors; release `develop` to `main` with a merge
  commit and a tag (`v1.2-increment1` .. `v1.5-increment4`); report the flow metrics; a short workflow review
  decides whether a policy or limit changes.

Increments: I1 2–15 Nov, I2 16–29 Nov, I3 30 Nov–13 Dec, I4 14–27 Dec 2026; feature freeze 27 Dec; release
period 28 Dec 2026 – 10 Jan 2027. The allocation of items to increments is a forecast; items are pulled in priority
order.

## Responsibilities (Kanban has no roles)

| Member | Process responsibility | Technical area |
|---|---|---|
| Yaman Almatar | Orders the backlog; contact with the supervisors; prepares the two-week review | Backend and architecture |
| Yousef Alzoubi | Keeps the board and its limits current; reports the flow metrics | Flutter app and web pages |
| Hasan Yahya | Owns the AI items (T-2 evaluation, FR-05) | AI and analysis |

All three develop, test, review and document.

## Flow metrics (reported every two weeks)

| Metric | Definition | Source |
|---|---|---|
| WIP | Items in In Progress + Review now | Board / project insights |
| Throughput | Items that reached Done per week | Merged pull requests per week |
| Work item age | Now minus the first commit on the item's branch, for unfinished items | Open pull requests and branches |
| Cycle time | Merge time minus the first commit on the item's branch, for finished items | Merged pull requests |

T-5 builds a small script that exports these values with the GitHub CLI.

## Commits and credit

Commit from your own GitHub account. Add a `Co-authored-by:` trailer only for teammates who actually worked on that
commit with you (see `CONTRIBUTING.md`).
