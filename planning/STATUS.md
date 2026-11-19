# STATUS — 2026-11-19
Branch: feat/fr04-rules
Task: TASK-42 — FR-04 Part 2: the quality rules, the score, and include or exclude
Done: services/quality_rules.py (pure Python, RULES_VERSION 1, five flags, score, bands) evaluates every response of a survey on read.
  QualityService.evaluate_survey (owner only, P-20 lock, 4 queries), set_inclusion, exclude_flagged, include_all (one bulk update, atomic).
  Analytics charts and sentiment counts use included responses only and leave attention questions out; lock and response_count stay on submitted; included_count added.
Changes: 6 modified, 6 new, 0 deleted — backend/services/quality_rules.py, backend/services/quality_service.py, backend/services/analysis_service.py, backend/repositories/, backend/tests/
Tests: rule tests 40 passed in 0.16s; task files 176 passed in 16.71s; whole suite 1013 passed in 74.70s (once, before commit); full suites run in CI
Check: OK
Committed: yes (start commit cd58459; change commit holds this file)
Open questions: none
Next: board W-04 — quality panel, confirmation pages and the web question form
