# STATUS — 2026-11-20
Branch: fix/fr05-w07-followups
Task: TASK-50 — follow-ups of FR-05 (board W-05b) and FR-07/FR-09 (board W-07)
Done: W-05b state 7 "Analysed 0 of Y answers." line; both messages in the new .question-sentiment__message box;
  bar widths by the largest remainder (sum to 100, labels unchanged); response pages get submitted_on (a date);
  QualityService.expected_answer is public. 10 new tests (1, 7, 2); one existing test renamed (Constraint A).
Changes: 10 modified, 1 new, 0 deleted (plus this file) — backend/apps/analysis/views.py, backend/apps/analysis/response_views.py, backend/apps/analysis/templates/analysis/analytics_dashboard.html, backend/static/css/site.css, backend/tests/views/test_sentiment_shares.py
Tests: task files 120 passed (110 before); whole backend suite 1199 passed (1189 before); full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-50 change commit holds this file)
Open questions: none
Next: the advisor reviews the analytics page and both response pages on a local server; Yaman or Hasan approves; Yousef merges
