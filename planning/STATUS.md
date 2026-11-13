# STATUS — 2026-11-13
Branch: fix/question-type-labels
Task: TASK-24B — sentence-case question type and account labels, Arabic answers right to left, refs #61
Done: commit 1: QUESTION_TYPE_LABELS for the question form and analytics badge; dir="auto" on text answers.
  commit 2: USER_TYPE_LABELS for home and the admin user list; home prints role_label and account_status_label;
  QuestionService type_label (manage questions, answer page) uses QUESTION_TYPE_LABELS. Enum labels unchanged, no migration.
Changes: 7 modified, 1 new, 0 deleted — backend/core/enums.py, backend/apps/users/views.py, backend/apps/admin_panel/views.py,
  backend/services/question_service.py, backend/tests/views/test_account_labels.py
Tests: changed and new files only (D-129): 41 passed (6 new) in commit 2; 9 passed (6 new) in commit 1; full suite runs in CI
Check: OK (System check identified no issues); makemigrations --check: No changes detected
Committed: yes (fix: sentence-case account labels (TASK-24B))
Open questions: none; manage_questions.html:105 {{ form.question_type }} is the select widget, kept as the advisor decided
Next: CI green, then Yaman approves and merges into develop; FR-01, FR-02 and FR-06 stay code complete.
