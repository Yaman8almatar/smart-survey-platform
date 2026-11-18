# STATUS — 2026-11-18
Branch: feat/w05a-sentiment-panel
Task: TASK-36 — W-05a: the sentiment panel of the analytics page (T-9, #72)
Done: "Sentiment of open answers" panel in six states (count line, worker hint, failed reasons + Retry, doughnut with centre total, captions);
  overdue rule by due time (oldest_due_at, has_stale_running, OVERDUE_AFTER); reset_failed sets next_attempt_at=now; retry refused while locked.
Changes: 10 modified, 2 new, 0 deleted — services/analysis_service.py, repositories/analysis_repository.py, apps/analysis/views.py, analytics_dashboard.html, tests/views/test_analytics_sentiment_panel_view.py
Tests: 6 files (test_analysis_worker, test_analysis_service, test_results_lock, test_analytics_dashboard_view, test_analytics_results_lock_view, test_analytics_sentiment_panel_view): 103 passed; whole suite once (D-169): 794 passed in 41.29s
Check: OK (System check identified no issues; makemigrations --check: No changes detected; node --check site.js OK)
Committed: yes (work commit on feat/w05a-sentiment-panel, see PR)
Open questions: none; the panel is not checked in a browser (no server started, D-103), covered by the view tests
Next: advisor reads the diff after Django CI is green; Yaman or Yousef approves; Yaman squash-merges
