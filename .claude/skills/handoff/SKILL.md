---
name: handoff
description: Write the end-of-task status to planning/STATUS.md and print it. Use at the end of every task or when the user types /handoff.
---

# Handoff

1. Collect changes. `git diff` alone misses new untracked files, so use all three:
   - `git branch --show-current`
   - `git status --short` and count modified (M), new (?? or A) and deleted (D) paths
   - `git diff --stat` for uncommitted work; if this task committed, also `git diff --stat develop...HEAD`
2. Verify (activate .venv first):
   - `python manage.py check` and keep its last line.
   - If any .py file changed in step 1, run `python -m pytest tests/services -q` and keep the final summary line.
     Otherwise write `skipped (no Python changes)`. If the database is not running, write the error type instead.
3. Overwrite planning/STATUS.md with exactly this block (max 15 lines):

```
# STATUS — <YYYY-MM-DD>
Branch: <branch>
Task: <one line>
Done: <1-3 lines>
Changes: <N modified, N new, N deleted> — <key paths, max 5>
Tests: <pytest summary line, or skipped / error type>
Check: <OK or the error>
Committed: <yes + short hash, or no>
Open questions: <none, or a short list>
Next: <one line>
```

4. Print the same block in the chat, then stop. Do not commit unless the task said so.
