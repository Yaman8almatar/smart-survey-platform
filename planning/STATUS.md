# STATUS — 2026-11-08
Branch: feat/fr06-drafts-backend
Task: TASK-20 Part 1 — FR-06 response drafts API (backend)
Done: GET, PUT and DELETE /surveys/{id}/draft/; a successful submit deletes the draft and copies started_at to the response;
  ensure_can_answer extracted from submit_response; migration 0006 (schema only, applied by the user); planning/API.md updated.
Changes: 12 modified, 4 new, 0 deleted — backend/services/response_service.py, backend/repositories/draft_repository.py,
  backend/apps/core/models/response_draft.py, backend/apps/api/views.py, planning/API.md
Tests: 562 passed in 602.40s (505 before; full run earlier this session, no .py file changed since)
Check: OK (System check identified no issues)
Committed: yes (feat: FR-06 response drafts API (TASK-20 Part 1))
Open questions: none; smoke reduced to one 401 call (D-124), the seven calls are left to the API tests and Part 2
Next: review, then Yaman merges into develop; Part 2 (the app, Yousef) is written after the merge.
