# STATUS — 2026-11-20
Branch: feat/fr07-response-pages
Task: TASK-49 — FR-07 and FR-09 responses one by one under a number; include or exclude one (board W-07, D-216)
Done: RESPONSE_NUMBER_ORDER and find_by_number; ResponseReviewService (list with show/order, one response with
  answers and verdict, fixed query counts); QualityService.set_response_inclusion; list and response pages,
  POST inclusion, shared _locked_card.html, "View responses" on the analytics page. 65 new tests (11, 21, 33).
Changes: 6 modified, 8 new, 0 deleted (plus this file) — backend/services/response_review_service.py, backend/services/quality_service.py, backend/apps/analysis/response_views.py, backend/apps/analysis/templates/analysis/response_detail.html, backend/tests/views/test_response_pages_view.py
Tests: task files 65 passed (0 before); whole backend suite 1189 passed (1124 before); full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-49 change commit holds this file)
Open questions: none
Next: the advisor reviews both pages on a local server; Yaman or Yousef approves; Hasan squash-merges
