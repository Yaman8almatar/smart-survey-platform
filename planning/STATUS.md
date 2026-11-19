# STATUS — 2026-11-20
Branch: feat/fr04-web
Task: TASK-43B — FR-04 Part 3 review fixes on PR #86: approved copy, attention section under the options, ready-text replacer
Done: Flags table "What it means" and the attention helper and limit captions now carry the approved copy (D-188).
  The attention divider and section sit under the option builder, before "Add question"; the required caption stays under "Required question".
  site.js fills the ready text with a replacer function, so "$&", "$'" and "$`" in an option stay literal.
Changes: 5 modified, 0 new, 0 deleted — analytics_dashboard.html, manage_questions.html, static/js/site.js, tests/views/ (2 files)
Tests: changed files 31 passed in 7.01s; whole suite 1081 passed in 51.56s (once, before commit); full suites run in CI
Check: OK
Committed: yes (the TASK-43B commit holds this file)
Open questions: none; site.js still not run in a browser (no server in this run)
Next: review of PR #86 (advisor opens both pages on a local server, D-170); then TASK-44
