# STATUS — 2026-11-06
Branch: fix/api-auth-throttling
Task: TASK-15 Part 3 — T-4 scoped throttling for the auth endpoints (#38)
Done: ScopedRateThrottle with auth_token 10/min, auth_refresh 30/min, auth_register 5/min, auth_logout 30/min; no default throttle, so health probes are free. Redis cache when REDIS_URL is set. throttles.py removed. 11 throttling tests, cache cleared per test. API.md: logout, rotation, 429, limits note.
Changes: 4 modified, 1 new, 1 deleted — backend/config/settings.py, backend/apps/api/views.py, backend/tests/api/test_throttling.py, backend/apps/api/throttles.py (deleted), planning/API.md
Tests: 352 passed, 247 warnings (baseline 341)
Check: OK (System check identified no issues)
Committed: yes — a1cfd34 (code, tests), 1486ba5 (API.md), this file in the final commit
Open questions: none
Next: open the PR to develop, move #38 to Review; after PR #50 merges, merge develop in (keep this STATUS.md). Part 4 waits (Review limit 2).
