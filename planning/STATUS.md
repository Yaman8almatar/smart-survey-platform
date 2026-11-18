# STATUS — 2026-11-16
Branch: feat/t9-remove-celery
Task: TASK-30 — T-9 Part 2: remove the dormant Celery path (P-23), issue #72
Done: Celery task, app, settings, pins and env lines removed; Redis kept for the throttle cache;
  prod stack worker runs run_analysis_worker after a healthy web; README says how to run the worker;
  malformed HF model URL raises AnalysisConfigError ("config") instead of being retried (D-151 (3)).
Changes: 10 modified, 0 new, 2 deleted — docker-compose.prod.yml, config/settings.py, requirements.txt,
  infrastructure/huggingface_client.py, apps/core/tasks.py + config/celery.py (deleted)
Tests: 30 passed in 11.36s (test_health_and_infrastructure, test_huggingface_client, test_run_analysis_worker); full suites run in CI
Check: OK (System check identified no issues (0 silenced))
Committed: yes, in the TASK-30 work commit on feat/t9-remove-celery
Open questions: diagrams/sequence-uc04-answer.md still describes USE_CELERY (diagrams/ out of scope)
Next: "Prod stack smoke" green; advisor reads the diff; Hasan or Yousef approves; Yaman squash-merges.
