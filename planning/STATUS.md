# STATUS — 2026-11-18
Branch: feat/fr03-matching-rule
Task: TASK-33 — FR-03 part 1: criteria lists and one matching rule (backend), issue #17
Done: TargetingCriteria holds regions, education_levels, occupations, marital_statuses, interests (region removed,
  migrations 0008 add, 0009 copy, 0010 remove); one P-17 rule in profile_matches_criteria and find_eligible_for_respondent,
  kept equal by a seeded parity test (P-18); survey detail uses ResponseService.ensure_can_answer (A-50).
Changes: 12 modified, 5 new, 0 deleted — services/targeting_service.py, repositories/survey_repository.py,
  apps/core/models/targeting_criteria.py, services/question_service.py, apps/core/migrations/0008-0010
Tests: 9 changed/related files: 272 passed; tests/views/test_targeting_criteria_view.py + test_surveys.py: 16 passed;
  demo seed test (run by the user): 3 passed; full suites run in CI
Check: OK (System check identified no issues (0 silenced)); makemigrations --check: No changes detected
Committed: yes, in the TASK-33 work commit on feat/fr03-matching-rule
Open questions: none
Next: Django CI green; advisor reads the diff; Hasan or Yousef approves; Yaman squash-merges; then TASK-34 (reach).
