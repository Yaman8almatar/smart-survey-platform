# STATUS — 2026-11-06
Branch: fix/api-auth-throttling
Task: D-097 — close the X-Forwarded-For throttle bypass found in the review of PR #51 (T-4, #38)
Done: REST_FRAMEWORK NUM_PROXIES from env, default 0, so throttles key on REMOTE_ADDR. New test: changing X-Forwarded-For does not reset the auth_token limit (failed 401 != 429 before, passes after). .env.example and API.md Throttling section updated. #38 boxes ticked.
Changes: 4 modified, 0 new, 0 deleted — backend/config/settings.py, backend/tests/api/test_throttling.py, backend/.env.example, planning/API.md
Tests: 353 passed, 248 warnings
Check: OK (System check identified no issues)
Committed: yes — 0794c03 (fix, pushed), this file in a separate commit (no amend after push)
Open questions: PR #50 also edits backend/.env.example; expect a small conflict when develop is merged in.
Next: Django CI green on PR #51, then teammate approval and comprehension answer; after PR #50 merges, merge develop in.
