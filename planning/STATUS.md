# STATUS — 2026-11-07
Branch: feat/t8-design-app
Task: TASK-17 Part B review fix — StateMessage start-aligned as in fr02-states.png (PR #57)
Done: StateMessage column starts at the leading edge (no centred text); survey list load error uses
  Icons.cloud_off_outlined, empty list has no icon; copy unchanged; new leading-edge alignment test.
Changes: 3 modified, 0 new, 0 deleted — frontend/lib/widgets/state_message.dart,
  frontend/lib/features/surveys/eligible_surveys_screen.dart, frontend/test/widgets/state_message_test.dart
Tests: skipped (no Python changes); flutter test 49 passed (before 48); flutter analyze no issues
Check: OK (System check identified no issues)
Committed: yes (second commit on PR #57, fix: StateMessage starts at the leading edge)
Open questions: none
Next: reviewer compares screenshots with documentation/design/; Yaman merges; TASK-16 Part 2 starts on top.
