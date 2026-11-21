# STATUS — 2026-11-21
Branch: feat/fr13-advanced-analytics
Task: TASK-56 — FR-13 one filter by gender, age group or governorate, comparison tables, responses over time (#27)
Done: service filter options (pooled per dimension), filtered question summaries with _filter_can_show, group_table for choice
  and rating questions, responses_over_time; one repository method; "Filter results" card, notes, comparison tables and the
  "Responses over time" bar chart (site.js). No migration, no API or app change.
Changes: 7 modified, 3 new, 0 deleted (plus this file) — backend/services/analysis_service.py, backend/repositories/response_repository.py, backend/apps/analysis/views.py, backend/apps/analysis/templates/analysis/analytics_dashboard.html, backend/static/js/site.js
Tests: task files 81 passed (35 new); whole backend suite 1454 passed (1419 before); full suites run in CI
Check: System check identified no issues (0 silenced). makemigrations --check: No changes detected
Committed: yes (the TASK-56 change commit holds this file)
Open questions: none (only Constraint E's test changed)
Next: Yaman or Hasan reviews and approves the PR from his own account; then Yousef merges into develop
