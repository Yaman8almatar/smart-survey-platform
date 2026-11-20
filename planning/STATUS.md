# STATUS — 2026-11-20
Branch: fix/question-options-type
Task: TASK-47 — question form: options left over from another type no longer block the save (D-194 (5))
Done: QuestionForm.clean blanks cleaned options for a non-multiple-choice type, before the early return;
  the bound field and option_lines keep the posted value; the service rule is unchanged. 6 new tests (3 form, 3 page).
Changes: 3 modified, 0 new, 0 deleted (plus this file) — backend/apps/surveys/forms.py, backend/tests/views/test_question_form.py, backend/tests/views/test_attention_question_form_view.py
Tests: task files 21 passed (5 of the 6 new failed before the fix); whole backend suite 1096 passed; full suites run in CI
Check: System check identified no issues (0 silenced).
Committed: yes (the TASK-47 change commit holds this file)
Open questions: none
Next: Yaman or Yousef reviews and approves the PR; Yaman merges with a squash
