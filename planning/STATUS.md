# STATUS — 2026-11-18
Branch: feat/fr03-targeting-web
Task: TASK-35 — FR-03 Part 3: the W-03 targeting page and the publish confirmation (web)
Done: Targeting page with gender segments, age fields, chips for five lists and a live reach card (seven states, copy only in the template);
  saving writes all five lists (closes D-163 (2)); Publish now opens a GET confirmation page and then POSTs; signal_ring gains text/decorative/empty arc;
  create_synthetic_respondents --delete runs without DEBUG (D-166 (5)); TargetingCriteriaForm removed.
Changes: 13 modified, 7 new, 0 deleted — apps/surveys/views.py, forms.py, templates/surveys/targeting_criteria.html, publish_confirm.html, static/js/site.js
Tests: 6 files (test_design_shell, test_targeting_criteria_view, test_targeting_reach_view, test_publish_confirm_view, test_create_synthetic_respondents, test_question_form): 50 passed; node --check site.js OK; full suites run in CI
Check: OK (System check identified no issues; makemigrations --check: No changes detected)
Committed: yes (work commit on feat/fr03-targeting-web, see PR)
Open questions: none; the live reach and layout are not checked in a browser (no server started, D-103), covered by the reviewer's manual check
Next: advisor reads the diff after Django CI is green; Yaman or Yousef approves; Yaman squash-merges
