# STATUS — 2026-11-19
Branch: feat/fr04-evidence
Task: TASK-41 — FR-04 Part 1: evidence at submit, attention questions, response snapshot; respondent web pages retired
Done: ResponseQuality (timings, active_ms, attention, rating facts, keyed device hash, signals_ok) and the profile snapshot are written in the submit transaction; drafts keep cumulative timings.
  Attention checks (max 2, MC/rating, forced required, expected answer) in QuestionService and the publish check; delete_survey refuses a survey with responses.
  Six respondent web pages removed; /respondent/ sends respondents to the app. Migrations 0012 (schema) and 0013 (snapshot fill).
Changes: 26 modified, 12 new, 7 deleted — backend/services/quality_service.py, backend/services/response_service.py, backend/apps/core/migrations/0012-0013, backend/apps/responses/, planning/API.md
Tests: task files 158 passed in 16.66s; whole suite 942 passed in 47.15s (once, before commit); full suites run in CI
Check: OK
Committed: yes (start commit d030c3e; change commit holds this file)
Open questions: none
Next: TASK-42 — flags, score and include/exclude from the stored evidence
