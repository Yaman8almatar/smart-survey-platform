# STATUS — 2026-11-19
Branch: feat/t2-model-evaluation
Task: TASK-37 — T-2: choose the sentiment model by the NFR-07 protocol (evaluation only, #36)
Done: protocol v1 then v1.1 frozen before any run; gold_v1 (150 ar + 150 en, every cell full) after the overlap filter (1,845 dropped);
  M0-M5 and R1 (M5 ar + M4 en) run on CPU; winner M4 (clapAI/roberta-base-multilingual-sentiment), tied with R1, decided by rule 4b (neutral recall).
Changes: 1 modified (planning/STATUS.md), 28 new, 0 deleted — evaluation/PROTOCOL.md, LEAKAGE.md, *.py, gold_v1_ids.csv, results/results.md
Tests: skipped (no backend, tools or frontend code changes); audit_agreement.py reports blank audit files and exits 0; full suites run in CI
Check: OK (System check identified no issues (0 silenced).)
Committed: yes (start 6e23c40, protocol da60431, gold set 14a5709, protocol v1.1 6eb82a1, results: see PR)
Open questions: M4 p95 latency 611 ms on CPU (worker load in FR-05); members still to fill C:\t2\audit\ (about 20 min each)
Next: advisor reads results and diff (D-129); Yaman approves and squash-merges; FR-05 wires M4 into the worker
