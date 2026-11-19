# STATUS — 2026-11-20
Branch: feat/fr04-web
Task: TASK-43 — FR-04 Part 3, web: attention option on the question form, response quality panel, bulk include or exclude
Done: Question form marks a choice or rating question as an attention check, with expected answer, ready text and the two-option rule; list shows badge and usage.
  Analytics page shows the "Response quality" panel once results are open; exclude and include go through GET confirmation pages and CSRF POSTs.
  Riders: respondent home card in sentence case; services/survey_access.ensure_survey_owner replaces both _ensure_survey_owner copies.
Changes: 12 modified, 7 new, 0 deleted — backend/apps/surveys/, backend/apps/analysis/, backend/services/survey_access.py, backend/static/, backend/tests/
Tests: task files 67 passed in 9.40s; whole suite 1080 passed in 55.21s (once, before commit); full suites run in CI
Check: OK
Committed: yes (start commit dc8276e; change commit holds this file)
Open questions: flag meanings, the attention helper caption and the limit caption were not in the brief (see PR "Decisions taken alone"); site.js not run in a browser (no server in this run)
Next: review of the PR (advisor opens both pages on a local server, D-170); then TASK-44
