# STATUS — 2026-11-06
Branch: fix/api-duplicate-submit
Task: TASK-15 Part 4 — T-1 duplicate submit (#35, F-06, F-20, F-21)
Done: Only unique_response_per_survey_respondent maps to DuplicateResponse; API handler lost its IntegrityError branch (unknown -> 500 internal_error).
  Registration maps only users_email to "Email is already registered."; Celery dispatch reads settings.CELERY_ENABLED and logs failures.
  11 new tests: threaded race, patched pre-check race (201 then 409), other-constraint, 500, Answer constraint, dispatch, email constraint.
Changes: 6 modified, 0 new, 0 deleted — backend/services/response_service.py, backend/services/authentication_service.py, backend/apps/api/exceptions.py, backend/tests/services/, backend/tests/api/test_responses.py
Tests: 364 passed, 132 warnings in 206.84s
Check: OK (System check identified no issues)
Committed: yes — this commit (fix: map only named integrity constraints), pushed; PR to develop opened
Open questions: HoLqKoO lacks write access to project 1; #35 is still Ready (Yaman to move it or grant access)
Next: Django CI green, approval from Yaman or Yousef, #35 to Review (needs board access); then Part 5.
