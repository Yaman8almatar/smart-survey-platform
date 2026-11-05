# STATUS — 2026-11-06
Branch: chore/infra-split-compose
Task: TASK-15 Part 2 (T-6 #48) — split compose, deploy files, settings (F-12, F-13, F-17, F-18)
Done: demo compose restored from v1.1.2 (db only, 5432); optional docker-compose.prod.yml (no secret, no beat, no Redis port);
  .env.prod.example, .dockerignore, .gitattributes; Python 3.11 image, gunicorn 23.0.0, collectstatic fails loudly;
  IS_TESTING removed, CI sets SECURE_SSL_REDIRECT=false, WhiteNoise test warning filtered; README + .env.example notes.
Changes: 11 modified, 4 new, 0 deleted — docker-compose.yml, docker-compose.prod.yml, backend/config/settings.py, backend/Dockerfile, .github/workflows/django-ci.yml
Tests: 341 passed (local .env and CI-like DEBUG=False), run in a temp venv with the branch requirements
Check: OK (laptop .venv still has main's packages: no celery; fixed by the step 11 pip install)
Committed: yes, in the Part 2 commit
Open questions: prod stack build not run — image pull failed (lookup auth.docker.io: no such host); compose config validated instead
Next: review + squash merge, then step 11 (backup demo DB, switch to develop, pip install, migrate, check, pytest, Flutter smoke)
