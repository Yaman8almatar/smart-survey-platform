# STATUS — 2026-11-19
Branch: chore/t9-smoke-model-manifest
Task: TASK-40 (#72, #19): smoke runs `run_analysis_worker --once`; every model file checked against a committed manifest
Done: prod smoke step "Worker command runs one batch" requires "No pending sentiment results."; M4 manifest (5 files, each verified against its Hub etag) replaces SENTIMENT_MODEL_SHA256.
Done: LocalTransformersAnalyzer(model_path, model_id, manifest) refuses any missing or changed file; build_analyzer and check_deployed.py read it with read_manifest.
Done: --check three labels; deployed check 0/300 differing, 5 of 5 files verified, load 7.76 s, p95 89 ms.
Changes: 12 modified, 1 new, 0 deleted — backend/infrastructure/local_analyzer.py, model_manifests/clapAI__roberta-base-multilingual-sentiment.sha256, .github/workflows/prod-stack-smoke.yml, evaluation/check_deployed.py, backend/tests/infrastructure/test_local_analyzer.py
Tests: task files 51 passed in 4.67s; whole suite 849 passed in 42.87s; full suites run in CI
Check: OK (System check identified no issues)
Committed: yes (change commit on chore/t9-smoke-model-manifest; start commit aa0a79a)
Open questions: none
Next: review (advisor reads the diff; Hasan or Yousef approves; Yaman squash-merges)
