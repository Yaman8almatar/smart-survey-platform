# STATUS — 2026-11-20
Branch: feat/fr12-survey-review
Task: TASK-54 — FR-12 the admin approves or rejects each survey, with a reason, before it is published (#26)
Done: PENDING_REVIEW state + submitted_at/reviewed_at/reviewed_by/rejection_reason (migration 0015, not applied);
  SurveyService.submit_for_review replaces publish_survey; SurveyReviewService (list, count, review, approve with
  locked read and reach count, reject with reason); provider submit page, badge, returned line, dashboard card; admin queue and review pages.
Changes: 26 modified, 9 new, 0 deleted (plus this file) — backend/services/survey_review_service.py, backend/apps/core/models/survey.py, backend/apps/core/migrations/0015_fr12_survey_review.py, backend/apps/admin_panel/views.py, backend/apps/surveys/views.py
Tests: new files 67 passed; task service files 241 passed; provider views 26 passed; admin views + admin service 49 passed; whole backend suite 1330 passed (1263 before)
Check: System check identified no issues (0 silenced). makemigrations --check: No changes detected
Committed: yes (the TASK-54 change commit holds this file)
Open questions: none
Next: Hasan or Yousef reviews and approves the PR; after merge, back up the laptop database and migrate 0015 with the worker stopped
