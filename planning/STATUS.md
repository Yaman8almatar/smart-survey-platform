# STATUS — 2026-11-06
Branch: chore/infra-split-compose
Task: TASK-15 Part 2 follow-up (T-6 #48) — prove the production stack on a GitHub runner (PR #50)
Done: new non-required workflow Prod stack smoke (build, up --wait, readiness 200, worker running);
  first run found the worker crash (kombu 5.7.0 needs redis-py >= 6.1), fixed by pinning kombu==5.3.7;
  PR #50 Verification updated; temp venv ssv2 deleted.
Changes: 1 modified, 1 new, 0 deleted — .github/workflows/prod-stack-smoke.yml, backend/requirements.txt
Tests: skipped (no Python changes); CI on 62e60c8: test green, Prod stack smoke green
Check: ModuleNotFoundError (laptop .venv has main's packages, no celery; fixed by the step 11 pip install)
Committed: yes — 2f83723, 62e60c8, plus this status commit
Open questions: none
Next: approval by Yousef or Hasan with the comprehension answer, squash merge, then step 11 (move the laptop to develop)
