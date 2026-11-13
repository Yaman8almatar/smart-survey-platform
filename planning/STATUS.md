# STATUS — 2026-11-13
Branch: fix/question-type-labels
Task: TASK-24B — question type labels in sentence case, Arabic answers right to left, refs #61
Done: QUESTION_TYPE_LABELS map next to QuestionType (enum labels unchanged, no migration); the question form and the analytics badge
  use it; each text answer on the analytics page has dir="auto", and the icon spacing uses margin-inline-end.
Changes: 6 modified, 1 new, 0 deleted — backend/core/enums.py, backend/apps/surveys/forms.py, backend/apps/analysis/views.py,
  backend/apps/analysis/templates/analysis/analytics_dashboard.html, backend/tests/views/test_question_form.py
Tests: changed and new files only (D-129): 9 passed (6 new); full suite runs in CI
Check: OK (System check identified no issues); makemigrations --check: No changes detected
Committed: yes (fix: sentence-case question type labels and answer direction (TASK-24B))
Open questions: the acceptance grep still finds {{ form.question_type }} (manage_questions.html:105), which is the form widget, not a raw value;
  not fixed: home.html:31 {{ user_type }} and :35 {{ account_status }} print raw values; user_management.html:45 shows "Service Provider"
Next: review, then Yaman merges into develop; FR-01, FR-02 and FR-06 stay code complete.
