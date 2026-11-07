# STATUS — 2026-11-07
Branch: feat/t8-design-app
Task: TASK-17 Part B — design foundation v2 in the Flutter app (T-8, D-110)
Done: v2 tokens (SsColors, SsSpace, SsRadius, SsShadow, SsMotion, SsType.ring); AppTheme brand-deep app bar and v2 controls;
  shared SignalRing and StateMessage widgets; survey list uses StateMessage (copy unchanged); design pictures committed.
Changes: 3 modified, 11 new, 0 deleted — frontend/lib/theme/, frontend/lib/widgets/, frontend/test/widgets/,
  frontend/test/theme/, documentation/design/
Tests: skipped (no Python changes); flutter test 48 passed (before 38); flutter analyze no issues
Check: OK (System check identified no issues)
Committed: yes (style: design foundation v2 for the app, on feat/t8-design-app)
Open questions: StateMessage is centred — components.png does not show it; compare with fr02-states.png in review
Next: PR review against documentation/design/; TASK-16 Part 2 starts on top of this PR.
