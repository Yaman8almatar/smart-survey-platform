# STATUS — 2026-11-08
Branch: feat/fr06-drafts-app
Task: TASK-20 Part 2 — FR-06 drafts and resume in the app
Done: the app saves answers when the question changes or the respondent leaves; the start screen offers Continue or Start over;
  Continue opens the first unanswered question; dayPhrase moved to survey_parts.dart; contract tests use the planning/API.md JSON (D-125).
Changes: 10 modified, 0 new, 0 deleted — frontend/lib/features/answer/survey_answer_screen.dart, survey_start_screen.dart,
  answer_repository.dart, answer_models.dart, frontend/test/features/answer/answer_flow_test.dart
Tests: pytest skipped (no Python changes); flutter test 179 passed (148 before); flutter analyze no issues
Check: OK (System check identified no issues)
Committed: yes (feat: FR-06 drafts and resume in the app (TASK-20 Part 2))
Open questions: none; no manual check (D-125), first real use is the demo rehearsal before the release PR
Next: review, then Yaman merges into develop; FR-06 (#20) is then Done.
