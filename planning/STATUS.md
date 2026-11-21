# STATUS — 2026-11-21
Branch: feat/fr11-survey-lifecycle
Task: TASK-55 — FR-11 opening and closing dates, a response limit, pause and resume (#25)
Done: PAUSED state + opens_on/closes_on/target_responses (migration 0016, not applied); date and limit checks; close_past_end;
  locked submit that closes the survey at its limit; pause/resume; schedule rows, list lines, buttons, dashboard card, report value;
  app card shows " · Closes D Mon". Session 1: A-D and service/API tests; session 2: view tests, Flutter, runs, PR.
Changes: 29 modified, 6 new, 0 deleted (this file included) — backend/services/response_service.py, backend/services/survey_service.py, backend/repositories/survey_repository.py, backend/apps/core/migrations/0016_fr11_survey_lifecycle.py, frontend/lib/features/surveys/eligible_surveys_screen.dart
Tests: FR-11 task files 89 passed; whole backend suite 1419 passed (1330 before); flutter analyze no issues; flutter test 238 passed (235 before)
Check: System check identified no issues (0 silenced). makemigrations --check: No changes detected
Committed: yes (the TASK-55 change commit holds this file)
Open questions: none (two tests outside Constraint G changed under D-236)
Next: Yaman or Yousef reviews and approves the PR; after merge, back up the laptop database and migrate 0016 with the worker stopped
