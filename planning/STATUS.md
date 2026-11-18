# STATUS — 2026-11-18
Branch: feat/fr03-reach
Task: TASK-34 — FR-03 Part 2: the reach count, its privacy band and synthetic respondents (backend)
Done: disclosure.band (P-19); ProfileRepository.count_pool/count_matching (third form, parity-tested); TargetingService.build_criteria/reach;
  POST /surveys/<id>/targeting/reach/ (JSON, TargetingListsForm); Survey.reach_at_publish set at publish; SurveyService.get_publish_preview;
  create_synthetic_respondents command (DEBUG only); migration 0011 applied locally, 500 synthetic respondents created.
Changes: 10 modified, 6 new, 0 deleted — services/disclosure.py, repositories/profile_repository.py, services/targeting_service.py, apps/surveys/views.py, apps/core/management/commands/create_synthetic_respondents.py
Tests: 6 files (test_disclosure, test_targeting_service, test_survey_service, test_targeting_reach_view, test_targeting_criteria_view, test_create_synthetic_respondents): 163 passed in 352.29s; full suites run in CI
Check: OK (System check identified no issues; makemigrations --check: No changes detected)
Committed: yes (see PR)
Open questions: "everyone" returns the unbanded pool total, as specified, so a pool of 1-4 shows its size; complementary criteria can still be differenced (band limit)
Next: advisor reads the diff after CI is green; Hasan or Yousef approves; then TASK-35 builds the W-03 page on this endpoint
