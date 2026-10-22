# Contributing

This guide is for the three team members and for the graduation committee. It describes how work moves
from a laptop to a release, so the history on GitHub shows who did what and when.

## Branches

| Branch | Purpose | Updated by |
|---|---|---|
| `main` | Releases only. Every merge into `main` is tagged. | A pull request from `develop` at the end of a sprint |
| `develop` | Integration branch. Always runnable. | Pull requests from short-lived branches, with green CI |
| short-lived | One task each, created from `develop`. | Its author; deleted after merge |

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
for example `fix/ai-arabic-label-mapping` or `docs/sprint-1-plan`.

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

The team often works together on one laptop, so the commit author is the laptop owner. To credit
everyone who took part, end the commit message with one `Co-authored-by:` trailer per teammate who
paired on that commit, and only for them. The exact lines are in `CLAUDE.md`, section
"Team and commit credit":

```text
feat: add survey list endpoint for the mobile client

Co-authored-by: Yousef812005 <alzby7906@gmail.com>
Co-authored-by: HoLqKoO <54415481+HoLqKoO@users.noreply.github.com>
```

GitHub credits a co-author (avatar on the commit and a contribution on their profile) only when the email
in the trailer is linked to that person's GitHub account. Each member should check
GitHub > Settings > Emails, or use their `<id>+<username>@users.noreply.github.com` address.

## Pull requests and merging

1. Push the branch and open a pull request into `develop`.
2. Wait for the **Django CI** check to pass. Do not merge on red.
3. Merge with **Squash and merge**, keeping a Conventional Commit title and the co-author trailers in
   the squash message, then delete the branch.

At the end of a sprint, open a pull request from `develop` into `main` and merge it with a
**merge commit** titled `Release vX.Y — Sprint N`, then tag that commit.

## Versions and tags

| Tag | Meaning |
|---|---|
| `V1.0` | Original junior project submission |
| `v1.0-junior-final` | Junior project final state, including the report and CI |
| `v1.1`, `v1.2`, ... | One release per Graduation 1 sprint |
| `v2.0` | Graduation 1 final submission |

```powershell
git checkout main
git pull --ff-only
git tag -a v1.1 -m "Release v1.1 — Sprint 1"
git push origin v1.1
```

## Before opening a pull request

Run from `backend/` with the virtual environment active and the database up:

```powershell
python manage.py check
python -m pytest tests/services -q
```

Never commit `backend/.env`, tokens or other secrets.
