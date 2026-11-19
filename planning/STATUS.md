# STATUS — 2026-11-19
Branch: feat/fr05-local-model
Task: TASK-39 FR-05 (#19): the worker analyses with M4 locally on the CPU, weights checked
Done: SentimentAnalyzer gateway (local default, huggingface fallback); LocalTransformersAnalyzer loads M4 float32 once in the worker, refuses other SHA-256s; run_analysis_worker --check.
Done: deployed check: 0/300 labels differ from T-2; macro-F1 ar 0.703, en 0.764, headline 0.733; p50 52 ms, p95 89 ms (T-2 263, 611).
Changes: 12 modified, 2 renamed, 8 new, 0 deleted — backend/infrastructure/local_analyzer.py, sentiment_analyzer.py, services/analysis_service.py, evaluation/check_deployed.py, evaluation/results/deployed_check.md
Tests: task files 190 passed in 10.94s; whole suite 826 passed in 40.38s; full suites run in CI
Check: OK (System check identified no issues)
Committed: yes (feature commit on feat/fr05-local-model; start commit 10abdc2)
Open questions: none
Next: review (advisor reads diff and deployed check; Yaman or Yousef approves; Yaman squash-merges)
