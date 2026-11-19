# STATUS — 2026-11-20
Branch: feat/fr04-app
Task: TASK-44 — FR-04 Part 4, app: start mark, active time per question, install ID, A-04 notice
Done: The app saves a start mark (empty draft) when no draft exists and sends cumulative active ms per question on every save and the send, plus a random install ID on the send.
  The tracker counts only the shown question in the foreground, and a hidden app saves once. A timings-only save failure no longer asks "Leave without saving?".
  The A-04 notice is under the title in both start-screen heroes.
Changes: 9 modified, 4 new, 0 deleted — features/answer/ (active_time.dart new, screens, models, repository), core/device_id_store.dart, main.dart, tests
Tests: answer_flow_test 75 passed; repository + tracker + device ID 44 passed; whole Flutter suite 225 passed (192 before); flutter analyze no issues; full suites run in CI
Check: skipped (TASK-44 forbids backend commands)
Committed: yes (the TASK-44 change commit holds this file)
Open questions: none; not run on a device or against a live server (no flutter run in this task)
Next: advisor reads the diff; user checks signals_ok true for one real response from Chrome; Yaman or Hasan approves, Yaman merges
