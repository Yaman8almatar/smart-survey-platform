# STATUS — 2026-11-20
Branch: feat/fr16-shuffle-order
Task: TASK-52 — FR-16 shuffled order of questions and answer options, fixed per respondent (#30)
Done: Survey.shuffle_questions / shuffle_options (migration 0014, db_default=False, not applied here);
  services/presentation_order.respondent_order ranks items by sha256(scope:survey:respondent:item), nothing stored;
  get_response_form reorders for the respondent (order_index = position), choices only; create/edit forms carry both settings.
Changes: 7 modified, 6 new, 0 deleted (plus this file) — backend/services/presentation_order.py, backend/services/question_service.py, backend/services/survey_service.py, backend/apps/core/migrations/0014_fr16_shuffle_order.py, backend/apps/surveys/templates/surveys/
Tests: task files 28 passed (all new); whole backend suite 1247 passed (1219 before); full suites run in CI
Check: System check identified no issues (0 silenced). makemigrations --check: No changes detected
Committed: yes (the TASK-52 change commit holds this file)
Open questions: none
Next: the advisor reviews the PR; after the merge, back up the laptop database and run migrate with the worker stopped
