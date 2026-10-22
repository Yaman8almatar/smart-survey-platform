# Smart Survey Platform — Claude Code context

## Project
Academic graduation project (Syrian Private University). Django 4.2 + PostgreSQL 15 survey platform.
Graduation 1 goals: REST API for a Flutter client, feature expansion, upgrade of sentiment analysis
(Modern Standard Arabic + English, pretrained models only, no training).

## Architecture rules (non-negotiable)
- Dependency direction: views / API views -> services -> repositories -> models (Django ORM).
- Never call the ORM from views or API views. Never put business rules in views.
- Business rules, ownership checks, role checks and validation live in services/ only.
- External HTTP and AI calls live in infrastructure/ only.
- Any workflow that writes more than one row must use transaction.atomic inside the service.
- Every new business rule gets a test in tests/services/.

## Commands (Windows)
```
.\.venv\Scripts\activate
docker compose up -d
python manage.py check
python -m pytest tests/services -q
python manage.py runserver
```

## Git rules
- Never work on main. Branch from develop: feature/<name>, fix/<name>, chore/<name>.
- Never commit or push unless the task explicitly says so.
- Never commit .env, tokens or secrets.

## Team and commit credit
The three members work together on one laptop, so commits are authored by Yaman Almatar.
At the start of a session that will commit, ask which teammates are pairing, unless the prompt already says.
Add one trailer per pairing teammate at the end of every commit message in that session:
- Yousef Alzoubi -> `Co-authored-by: Yousef812005 <alzby7906@gmail.com>`
- Hasan Yahya -> `Co-authored-by: HoLqKoO <54415481+HoLqKoO@users.noreply.github.com>`
Never add a trailer for someone who did not take part.
Never add Claude or AI co-author trailers to commits or PRs.

## How to work
- Start any non-trivial task in Plan Mode and wait for approval.
- Read only the files named in the task; ask before scanning the whole repository.
- Do not edit applied migrations; create new ones.
- Do not touch Smart_Survey_Project_Documentation/.
- Finish every task with the /handoff skill. Keep replies short.

## Known issues (fix only when a task asks)
- K-01 ResponseService.submit_response is not atomic.
- K-02 Sentiment analysis runs synchronously inside submit_response.
- K-03 Region targeting is an exact string comparison on free text.
- K-06 .gitignore ignores docs/ — planning files live in planning/.

## Planning files
- planning/STATUS.md — current state, written by /handoff.
- Requirement IDs follow the report: FR-xx, UC-xx, TC-xx.
