# STATUS — 2026-11-20
Branch: feat/fr05-group-summary
Task: TASK-48 — FR-05 sentiment per open question and per group, small groups pooled (board W-05b, D-213)
Done: disclosure.pool_groups (P-15, DESIGN-INC2 3.6); get_survey_results(group_by) adds sentiment and an optional
  snapshot breakdown to every open-text summary; the "Group breakdown" GET card replaces "Analytics summary";
  each open question shows its bar, legend and group table. 28 new tests (10 helper, 11 service, 7 page).
Changes: 8 modified, 1 new, 0 deleted (plus this file) — backend/services/disclosure.py, backend/services/analysis_service.py, backend/apps/analysis/views.py, backend/apps/analysis/templates/analysis/analytics_dashboard.html, backend/tests/views/test_analytics_group_summary_view.py
Tests: task files 90 passed (62 before); whole backend suite 1124 passed (1096 before); full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-48 change commit holds this file)
Open questions: none
Next: the advisor reviews the page on a local server; Hasan or Yousef approves; Yaman squash-merges
