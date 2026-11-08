# STATUS — 2026-11-08
Branch: feat/fr01-answer-flow
Task: TASK-19 review fix (D-121) — start hero alignment and dialog title type on PR #62
Done: start hero column fills the content width; HeroBand pads inside the content width, so hero and sheet share one edge;
  dialogTheme title SsType.title in ink, content SsType.body in inkMuted (the profile discard dialog takes the same look).
Changes: 6 modified, 0 new, 0 deleted — frontend/lib/features/answer/survey_start_screen.dart, frontend/lib/features/profile/profile_hero.dart,
  frontend/lib/theme/app_theme.dart, frontend/test/features/answer/answer_flow_test.dart, frontend/test/theme/app_theme_test.dart
Tests: skipped (no Python changes); flutter analyze no issues; flutter test 148 passed (146 before)
Check: OK (System check identified no issues)
Committed: yes (fix: start hero alignment and dialog title type (TASK-19, D-121))
Open questions: board cards #15 and #20 need a manual move (Yousef's token has no project scope); open-text question in Arabic not sent end to end yet (D-120)
Next: Arabic open-text end-to-end send before the release PR; Yaman or Hasan approves; Yaman merges into develop.
