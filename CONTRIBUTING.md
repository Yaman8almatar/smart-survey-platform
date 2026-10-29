# Contributing

This guide is for the three team members and for the graduation committee. It describes how work moves
from a laptop to a release, so the history on GitHub shows who did what and when.

## Branches

| Branch | Purpose | Updated by |
|---|---|---|
| `main` | Releases only. Every merge into `main` is tagged. | A release pull request from `develop` every two weeks, or a hotfix pull request |
| `develop` | Integration branch. Always runnable. | Pull requests from short-lived branches, with green CI |
| short-lived | One task each, created from `develop`. | Its author; deleted after merge |
| `hotfix/<desc>` | An urgent change to a released version, created from `main`. | A pull request into `main`, then merged back into `develop` |

Never push directly to `main` or `develop`. Never force-push a shared branch.

## Short-lived branch names

Create every branch from an up-to-date `develop`:

```powershell
git checkout develop
git pull --ff-only
git checkout -b feature/api-survey-list
```

| Pattern | Use for |
|---|---|
| `feature/<area>-<desc>` | New behaviour |
| `fix/<area>-<desc>` | Bug fixes |
| `chore/<desc>` | Tooling, configuration, repository housekeeping |
| `docs/<desc>` | Documentation only |
| `test/<desc>` | Tests only |

Areas: `api`, `mobile`, `web`, `ai`, `infra`. Use short lowercase words joined by hyphens,
for example `fix/ai-arabic-label-mapping` or `docs/increment-1-review`.

## Workflow on the board

The team uses Kanban. The workflow, the WIP limits and the policies are in
[`planning/KANBAN.md`](planning/KANBAN.md). In short:

- Pull the next item from **Ready** only when **In Progress** has fewer than 3 items, assign it to yourself and
  move it to In Progress when you create its branch.
- Move it to **Review** when the pull request is open, and to **Done** when it is merged into `develop`.
- A blocked item gets the label `blocked`, a comment with the reason and a mention of a teammate.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/): `type: summary`, with the
summary in the imperative and under about 70 characters.

| Type | Use for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `refactor` | Code change that keeps behaviour |
| `test` | Adding or changing tests |
| `docs` | Documentation |
| `chore` | Maintenance, dependencies, configuration |
| `ci` | GitHub Actions workflow |

Example: `feat: add survey list endpoint for the mobile client`.

## Pair work and co-author credit

The team works together on some days and alone from home on others. Always commit under your own
GitHub account (`git config user.name` and `git config user.email` set on every machine you use).
When teammates worked with you on a commit, end the commit message with one `Co-authored-by:` trailer
per teammate who took part, and only for them. A commit you wrote alone has no trailer. The trailer
lines are:

```text
Co-authored-by: Yousef812005 <alzby7906@gmail.com>
Co-authored-by: HoLqKoO <54415481+HoLqKoO@users.noreply.github.com>
```

For example, a commit message that credits both teammates looks like this:

```text
feat: add survey list endpoint for the mobile client

Co-authored-by: Yousef812005 <alzby7906@gmail.com>
Co-authored-by: HoLqKoO <54415481+HoLqKoO@users.noreply.github.com>
```

GitHub credits a co-author (avatar on the commit and a contribution on their profile) only when the email
in the trailer is linked to that person's GitHub account. Each member should check
GitHub > Settings > Emails, or use their `<id>+<username>@users.noreply.github.com` address.

## Pull requests and merging

1. Push the branch and open a pull request into `develop` that references its issue.
2. Ask a teammate who did not write the change to review and approve it.
3. Wait for the **Django CI** check (and **Flutter CI** when `frontend/` changed) to pass. Do not merge on red.
4. Merge with **Squash and merge**, keeping a Conventional Commit title and the co-author trailers in
   the squash message, then delete the branch.

At the end of each Increment (every two weeks), open a pull request from `develop` into `main` and merge
it with a **merge commit** titled `Release vX.Y — Increment N`, then tag that commit.

A **hotfix** starts from `main` (`git checkout -b hotfix/<desc> origin/main`), is merged into `main` by a
pull request with a merge commit and tagged as a patch (`v1.1.2`), and is then merged back into `develop`
by a second pull request, also with a merge commit (never a squash, so `develop` contains the same commits).

## Versions and tags

| Tag | Meaning |
|---|---|
| `V1.0` | Original junior project submission |
| `v1.0-junior-final` | Junior project final state, including the report and CI |
| `v1.1-iteration0` | End of Iteration 0 (Seminar 1) |
| `v1.1.1`, `v1.1.2`, ... | Patch releases (repository housekeeping, hotfixes) |
| `v1.2-increment1` .. `v1.5-increment4` | One release per Graduation 1 Increment |
| `v2.0` | Graduation 1 final submission |

```powershell
git checkout main
git pull --ff-only
git tag -a v1.2-increment1 -m "Release v1.2 — Increment 1"
git push origin v1.2-increment1
```

## Before opening a pull request

Run from `backend/` with the virtual environment active and the database up:

```powershell
python manage.py check
python -m pytest tests -q
```

Never commit `backend/.env`, tokens or other secrets.
