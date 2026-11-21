# STATUS — 2026-11-21
Branch: feat/fr15-permissions-throttle
Task: TASK-57 — FR-15 Part A, role permissions proven in the service layer and the submit endpoint throttled (#29)
Done: scope survey_submit 10/min on POST /surveys/{id}/responses/ (per respondent, 429 throttled); role matrix test,
  53 rows x 2 wrong roles = 106 refused calls with row counts unchanged, 2 listed exceptions, ast guard test. No service
  method needed a new role check. API.md: submit 429, Throttling row. No migration, no app change.
Changes: 3 modified, 2 new, 0 deleted (plus this file) — backend/config/settings.py, backend/apps/api/views.py, planning/API.md, backend/tests/services/test_role_permissions.py, backend/tests/api/test_submit_throttling.py
Tests: task files 147 passed (113 new); whole backend suite 1571 passed (1458 before); full suites run in CI
Check: System check identified no issues (0 silenced). makemigrations --check: No changes detected
Committed: yes (the TASK-57 change commit holds this file)
Open questions: none
Next: the advisor reviews the diff and reruns the tests; Yaman approves and squash-merges the PR into develop
