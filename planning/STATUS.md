# STATUS — 2026-11-18
Branch: feat/p20-results-lock
Task: TASK-38 — P-20: a survey's results open at 5 responses (FR-09 rule, D-168)
Done: disclosure.results_open; get_survey_results returns only {survey_id, response_count, locked, min_responses} below MIN_GROUP_SIZE
  and reads no answers, results or questions; the analytics page shows a locked card instead of the results; chart scripts do not run when locked.
Changes: 9 modified, 3 new, 0 deleted — services/disclosure.py, services/analysis_service.py, apps/analysis/views.py, analytics_dashboard.html, tests/conftest.py
Tests: 6 files (test_disclosure, test_results_lock, test_analytics_results_lock_view, test_analysis_service, test_analysis_worker, test_analytics_dashboard_view): 84 passed; whole suite once (D-169): 765 passed in 38.00s
Check: OK (System check identified no issues; makemigrations --check: No changes detected)
Committed: yes (work commit on feat/p20-results-lock, see PR)
Open questions: none; the locked page is not checked in a browser (no server started, D-103), covered by the view tests
Next: advisor reads the diff after Django CI is green; Hasan or Yousef approves; Yaman squash-merges
