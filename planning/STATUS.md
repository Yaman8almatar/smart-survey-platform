# STATUS — 2026-11-20
Branch: feat/fr14-export
Task: TASK-51 — FR-14 export the included responses and their quality verdicts to CSV and Excel (#28)
Done: ResponseReviewService.export_responses (8 queries, included rows under the list numbers) and
  AnalysisRepository.find_statuses_by_answer_for_survey; export_views.py with one shared table, the formula
  guard, CSV (utf-8-sig) and Excel (sheet "Responses"); two GET-only URLs; Download CSV/Excel and the caption on W-07.
Changes: 5 modified, 3 new, 0 deleted (plus this file) — backend/services/response_review_service.py, backend/apps/analysis/export_views.py, backend/apps/analysis/templates/analysis/response_list.html, backend/tests/services/test_response_export_service.py, backend/tests/views/test_response_export_view.py
Tests: task files 19 passed (8 service, 11 view); whole backend suite 1218 passed (1199 before); full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-51 change commit holds this file)
Open questions: none
Next: the advisor opens both files from a local server; Hasan or Yousef approves; Yaman merges
