# STATUS — 2026-11-28
Branch: feat/fr10-invitation-link
Task: TASK-65 — FR-10 Part A: invitation link and QR code on the server, the API and the website (#24)
Done: Survey.invite_token + migration 0018 (not applied to the laptop DB); get_invitation / resolve_invitation in
  SurveyService; GET /api/v1/invitations/{token}/; Share button, share page, QR download (segno 1.6.6), copy script.
Changes: 18 modified, 6 new, 0 deleted — services/survey_service.py, apps/api/views.py, apps/surveys/views.py,
  apps/surveys/templates/surveys/share_survey.html, apps/core/migrations/0018_fr10_invite_token.py
Tests: 3 new files 46 passed; test_invitation_service + test_role_permissions 136 passed; whole backend suite
  1705 passed (1655 before); full suites run in CI
Check: System check identified no issues (0 silenced); makemigrations --check --dry-run: No changes detected
Committed: yes, in the TASK-65 change commit on top of the start commit 69c1297
Open questions: none
Next: advisor review and local share-page check; merge after the 30 Nov review; OPS-04 backs up and applies 0018
