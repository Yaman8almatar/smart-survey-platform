# STATUS — 2026-11-08
Branch: feat/t8-design-web
Task: TASK-17 Part A (T-8, D-110) — design foundation v2 on the Django web pages
Done: tokens.css with the v2 token block + Bootstrap mapping; site.css --ssp-* re-pointed, literals/gradients/uppercase
  removed, cards without shadow; navbar brand-deep 64px with signal mark and aria-current accent underline; light
  footer mark; partials/signal_ring.html (unused until FR-04/FR-08). Screenshots taken by the user (D-105, D-115).
Changes: 3 modified, 3 new, 0 deleted — backend/static/css/tokens.css, backend/static/css/site.css,
  backend/templates/base.html, backend/templates/partials/signal_ring.html, backend/tests/views/test_design_shell.py
Tests: 505 passed (503 + 2 new; backend diff unchanged since that run)
Check: OK (System check identified no issues)
Committed: yes (style: design foundation v2 for the web (TASK-17 Part A))
Open questions: question_type badge on analytics prints the raw value (template change, out of scope)
Next: advisor compares screenshots with web-shell.png; Yaman or Yousef approves; Yaman merges into develop.
