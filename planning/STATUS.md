# STATUS — 2026-10-23
Branch: feature/flutter-auth
Task: TASK-08 Part A — Flutter login and eligible-survey list on the real API
Done: ApiClient (Bearer, one shared refresh on 401), secure token store, auth + surveys features, AuthGate, sample home removed, CORS header test. Part B not started.
Changes: 7 modified, 15 new, 1 deleted — frontend/lib/core/api/, frontend/lib/features/{auth,surveys}/, frontend/lib/app.dart, frontend/test/, backend/tests/api/test_cors_headers.py
Tests: flutter analyze clean; flutter test 28 passed; pytest 336 passed (full run)
Check: OK (System check identified no issues)
Committed: yes (ab73ad8, pushed; this status in a follow-up commit)
Open questions: first git push ran with no denial on my side; whether the permission prompt showed is for the user to confirm. Manual (release build on :5000, not -d chrome): login OK, reload keeps session OK, logout OK, wrong password OK, server down + Retry OK, provider message OK. Seed gives respondent an answered demo survey, so the list was empty until an extra survey was added locally.
Next: merge PR after CI is green, then Part B (register) on feature/flutter-register.
