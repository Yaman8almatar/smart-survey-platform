# STATUS — 2026-11-14
Branch: feat/t9-analysis-worker
Task: TASK-29 — T-9 analysis worker: sentiment leaves the submit request (K-02), issue #72
Done: submit writes one PENDING row per non-blank open-text answer in its transaction, no gateway call;
  run_analysis_worker claims batches (skip_locked), retries unavailable (30 s, 120 s, 3 attempts), reason codes;
  migration 0007_sentiment_worker_fields applied locally; status counts and retry_failed in AnalysisService.
Changes: 14 modified, 11 new, 0 deleted — services/analysis_service.py, repositories/analysis_repository.py,
  infrastructure/huggingface_client.py, apps/core/management/commands/run_analysis_worker.py, migrations/0007
Tests: 173 passed in 139.87s (changed files; the demo seed command's 2 tests passed in the user's run); full suite in CI
Check: OK (System check identified no issues)
Committed: yes, in the TASK-29 commit on feat/t9-analysis-worker
Open questions: Celery task removal waits for Q4 (P-23); provider page for the counts waits for W-05a
Next: advisor reads the diff; Hasan or Yousef approves; merge only after release PR v1.2-increment1 (D-148 (2)).
