# STATUS — 2026-11-06
Branch: fix/mobile-logout-server
Task: TASK-15 Part 6 (T-6, #48): Flutter logout calls auth/logout/ and always signs out
Done: AuthRepository.logout posts the refresh token to auth/logout/ (no auth header), ignores ApiException, always clears tokens.
  4 new TestApi tests (204, 400, network failure, no refresh token). API.md auth flow notes the client behaviour.
Changes: 3 modified, 1 new, 0 deleted — frontend/lib/features/auth/auth_repository.dart, frontend/test/features/auth/auth_repository_logout_test.dart, planning/API.md, planning/STATUS.md
Tests: skipped (no Python changes); flutter test: 38 passed; flutter analyze: No issues found
Check: OK (System check identified no issues)
Committed: no (goes into the Part 6 commit)
Open questions: none
Next: commit, push, open PR against develop; approval from Yaman or Hasan; #48 stays In Progress until Part 8.
