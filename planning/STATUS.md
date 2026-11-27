# STATUS — 2026-11-21
Branch: feat/fr15-email-recovery
Task: TASK-58 — FR-15 Part B, email confirmation before the first log-in and password recovery on the website (#29)
Done: User.email_verified (0017, existing rows true); AccountEmailService (confirm, resend, reset, 300 s rule, reset blacklists
  refresh tokens); log-in 403 email_not_confirmed; web pages confirm-email, resend, password-reset (+ link); app returns to
  log-in after registering and shows the website reset address. 0017 written, not applied to the laptop database.
Changes: 18 modified, 9 new, 0 deleted (plus this file) — backend/services/account_email_service.py, backend/apps/users/views.py, backend/apps/core/migrations/0017_fr15_email_verified.py, frontend/lib/features/auth/register_screen.dart, planning/API.md
Tests: task files 239 passed (76 new); whole backend 1647 passed (1571 before); Flutter auth files 10 passed (2 new),
  flutter test 240 passed (238 before); flutter analyze: No issues found; full suites run in CI
Check: System check identified no issues (0 silenced). makemigrations --check --dry-run: No changes detected
Committed: yes (the TASK-58 change commit holds this file)
Open questions: none
Next: the advisor reviews the diff and opens the pages locally; Yaman squash-merges; the laptop backs up and applies 0017
