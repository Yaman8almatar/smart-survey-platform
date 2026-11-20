# STATUS — 2026-11-20
Branch: feat/fr14-export
Task: TASK-51B — FR-14 review fix: clean control characters before the formula guard (#28, PR #95)
Done: export_table now writes every str cell as _guard(ILLEGAL_CHARACTERS_RE.sub("", cell)), headers included;
  response_export_xlsx appends the table as it is, so CSV and Excel hold the same cleaned, guarded text.
  New test: "\x07=1+1" comes out "'=1+1" in both files, Excel data_type "s"; the control-character test expects both clean.
Changes: 2 modified, 0 new, 0 deleted (plus this file) — backend/apps/analysis/export_views.py, backend/tests/views/test_response_export_view.py
Tests: task files 20 passed (19 before); whole backend suite 1219 passed (1218 before); full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-51B fix commit holds this file)
Open questions: none
Next: the advisor re-checks PR #95; Hasan or Yousef approves; Yaman merges
