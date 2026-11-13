# STATUS — 2026-11-13
Branch: fix/inc1-web-audit
Task: TASK-24 — web audit fixes: colour tokens, sentence case, visible sentiment failure (A-15, A-16, A-209), refs #61
Done: chart and mark colours read from tokens.css (ssToken/withAlpha in site.js); 29 labels in sentence case; .btn radius 12 px;
  AnalysisService.get_survey_results returns failed_count and the sentiment card shows a server-side failure notice.
Changes: 13 modified, 1 new, 0 deleted — backend/static/js/site.js, backend/apps/analysis/templates/analysis/analytics_dashboard.html,
  backend/services/analysis_service.py, backend/templates/base.html, backend/tests/views/test_analytics_dashboard_view.py
Tests: changed and new files only (D-129): 47 passed (4 new); full suite runs in CI (562 before)
Check: OK (System check identified no issues)
Committed: yes (fix: web colour tokens, sentence case and visible sentiment failure (TASK-24))
Open questions: none; manual check passed (screenshot approved by the advisor); session ran in bypass permissions mode
Next: review, then Yaman merges into develop; FR-01, FR-02 and FR-06 stay code complete.
