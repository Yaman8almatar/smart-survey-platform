# STATUS — 2026-11-06
Branch: chore/upgrade-django-5-2
Task: TASK-15 Part 7 (T-7, #49): upgrade the backend to Django 5.2 LTS
Done: Django 5.2.19, whitenoise 6.9.0, pytest-django 4.11.0; CI SECRET_KEY is a 66-char CI-only value; .env.example SECRET_KEY empty with key-generation notes.
  makemigrations --check: no changes; 0 warnings with -W default::DeprecationWarning. API smoke 200 x3; provider web, admin, Flutter login/list/logout passed.
Changes: 4 modified, 0 new, 0 deleted — backend/requirements.txt, .github/workflows/django-ci.yml, backend/.env.example, planning/STATUS.md
Tests: 411 passed, 1 xfailed (run after the upgrade; no .py files changed)
Check: OK (System check identified no issues)
Committed: no (goes into the Part 7 commit)
Open questions: none
Next: commit, push, open PR against develop; approval from Hasan or Yousef; #49 to Review.
