# STATUS — 2026-11-20
Branch: feat/fr08-survey-list
Task: TASK-53 — FR-08 survey list ranked by shared interests, with expected time, search and filters (#22)
Done: services/expected_time (median of >= 20 valid active_ms, else per-type estimate, ceil, min 1);
  eligible items ranked by shared interests (stable), plus expected_minutes and published_on (+1 query);
  app card "N questions · About M min", search field and All / Under 5 min / New this week chips, no-result state.
Changes: 10 modified, 5 new, 0 deleted (plus this file) — backend/services/expected_time.py, backend/services/survey_service.py, backend/repositories/survey_repository.py, backend/repositories/quality_repository.py, frontend/lib/features/surveys/eligible_surveys_screen.dart
Tests: backend task files 77 passed (16 new); whole backend suite 1263 passed (1247 before); Flutter task files 97 passed (10 new); flutter test 235 passed (225 before); flutter analyze no issues
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-53 change commit holds this file)
Open questions: none
Next: Yaman or Hasan reviews and approves the PR; the user checks the list, minutes, search and chips against the laptop server
