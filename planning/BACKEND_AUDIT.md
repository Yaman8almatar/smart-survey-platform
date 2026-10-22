# BACKEND AUDIT — 2026-10-23
Branch: chore/claude-setup (commit 75fd0bd). Read-only audit. Every line below comes from a command run in this session.

## Environment
| Item | Result |
|---|---|
| Repository path | `C:\Users\ASUS\Desktop\smart-survey-platform2` (ASCII, no spaces) |
| Python (.venv) | 3.11.9 |
| requirements.txt packages | all 6 match: Django 4.2.11, psycopg 3.1.18, python-dotenv 1.0.1, pytest 8.1.1, pytest-django 4.8.0, requests 2.31.0. Mismatches: none |
| Docker | 29.2.1, build a5c7197 |
| Git | 2.51.1.windows.1 |
| Flutter | `C:\SRC\flutter\bin\flutter.bat` exists, but `flutter --version` printed nothing in 120 s and again in 90 s (hung). `flutter doctor` not run. Flutter state: unverified |

## Skills
Skills listed as available in this session. Skills named in the task (`superpowers:verification-before-completion`, `engineering:code-review`, `engineering:tech-debt`) are all in the list. They were not loaded. Severity was rated by hand and each claim carries command output.
- project: find-skills, handoff, init, security-review, update-config, keybindings-help, code-review, simplify, fewer-permission-prompts, loop, schedule, claude-api, run, plugin-authoring
- anthropic-skills: built-in-browser, chrome-browser, computer-use, consolidate-memory, deep-research, docs, docx, explain-usage, google-workspace, import-memory, morning, pdf, pptx, schedule, setup-claude, skill-creator, xlsx
- superpowers: using-superpowers, brainstorming, diagnosing-superpowers, dispatching-parallel-agents, executing-plans, finishing-a-development-branch, receiving-code-review, requesting-code-review, subagent-driven-development, systematic-debugging, test-driven-development, using-git-worktrees, verification-before-completion, writing-plans, writing-skills
- engineering: architecture, code-review, debug, deploy-checklist, documentation, incident-response, standup, system-design, tech-debt, testing-strategy
- data: analyze, build-dashboard, create-viz, data-context-extractor, data-visualization, explore-data, sql-queries, statistical-analysis, validate-data, write-query
- design: accessibility-review, design-critique, design-handoff, design-system, research-synthesis, user-research, ux-copy
- figma: figma-code-connect, figma-code-workflows, figma-create-new-file, figma-design-to-code, figma-generate-design, figma-generate-diagram, figma-generate-library, figma-generative-plugins, figma-implement-motion, figma-shaders, figma-spec, figma-swiftui, figma-use, figma-use-figjam, figma-use-motion, figma-use-slides
- caveman: caveman-init, cavecrew, caveman, caveman-commit, caveman-compress, caveman-discover, caveman-evidence-review, caveman-explore, caveman-help, caveman-learn, caveman-manage, caveman-optimize, caveman-review, caveman-setup, caveman-stats, investigate-first, lean-build, migration, safe-refactor, surgical-patch, verify-and-stop
- searchfit-seo: create-content, create-topic, generate-schema, keyword-cluster, seo-check, translate-content, ai-visibility, broken-links, content-brief, content-strategy, content-translation, internal-linking, keyword-clustering, on-page-seo, schema-markup, seo-audit, technical-seo
- fastly-agent-toolkit: falco, fastlike, fastly, fastly-cli, fastly-fiddle, fastly-ngwaf, fastly-reference-architectures, fastly-stats, viceroy, xvcl
- claude-code-setup: claude-automation-recommender
- frontend-design: frontend-design
- rtl-chat-fixer: rtl-chat
- desktop-commander: ai-tools-setup, computer-health-check, desktop-commander-overview, knowledge-base, obsidian-vault, terminal
- dataviz: dataviz
- artifact: artifact-design, artifact-diagramming, artifact-capabilities

## Database
`docker ps -a` (running containers only):
| Name | Status | Ports |
|---|---|---|
| smart_survey_db_new | Up 8 minutes | 0.0.0.0:5433->5432/tcp |
| smart_survey_db | Up 8 minutes | 0.0.0.0:5432->5432/tcp |

- Django uses `HOST=127.0.0.1 PORT=5432` (from `settings.DATABASES["default"]`). Container `smart_survey_db` publishes 5432, so the STOP condition did not trigger.
- `docker-compose.yml` defines only `smart_survey_db_new` and publishes **5433**. `docker compose up -d` printed `Container smart_survey_db_new Running`. The DB Django uses (5432) is a container outside this compose file.
- `showmigrations`: all applied (admin 0001-0003, auth 0001-0012, contenttypes 0001-0002, core 0001, sessions 0001). Unapplied: none.
- `makemigrations --check --dry-run`: `No changes detected` (exit 0). Drift: none.

## Tests
- `python -m pytest tests/services -q`: `168 passed in 120.08s (0:02:00)`.
- `--collect-only -q`: `168 tests collected`.
- `def test_` count in tests/services/*.py: 165. Difference of 3: `tests/services/test_profile_service.py:123` has `@pytest.mark.parametrize("age", [0, -1, 121, "30"])`, which turns 1 function into 4 cases (165 - 1 + 4 = 168). Per file collected vs defs: only test_profile_service.py differs (10 vs 7).
- The report's 163 matches neither number. The report is stale.
- Earlier in this session, with the DB unreachable, the same suite gave errors (`psycopg.OperationalError ... Socket is not connected`). After the containers were up it passed.

## Smoke test
`apps/core/management/commands/seed_demo_data.py` is idempotent (upserts by email/title/order_index, `@transaction.atomic`). It was run twice without error. It resets the three demo passwords on the dev DB.
`planning/_smoke.py` used `Client.force_login` (no password POST), covered project URLs only (Django `admin/` excluded), and was deleted.

Parameter-free URLs. Cell = HTTP status; `302` = redirect to `/users/login/`.
| URL name | anonymous | admin | service_provider | respondent |
|---|---|---|---|---|
| home | 200 | 200 | 200 | 200 |
| admin_panel:admin_dashboard | 302 | 200 | 302 | 302 |
| admin_panel:user_management | 302 | 200 | 302 | 302 |
| admin_panel:system_reports | 302 | 200 | 302 | 302 |
| responses:respondent_dashboard | 302 | 302 | 302 | 200 |
| responses:demographic_profile | 302 | 302 | 302 | 200 |
| responses:eligible_surveys | 302 | 302 | 302 | 200 |
| responses:answered_surveys | 302 | 302 | 302 | 200 |
| responses:submission_confirmation | 302 | 302 | 302 | 200 |
| surveys:provider_dashboard | 302 | 302 | 200 | 302 |
| surveys:survey_list | 302 | 302 | 200 | 302 |
| surveys:create_survey | 302 | 302 | 200 | 302 |
| users:register_service_provider | 200 | 200 | 200 | 200 |
| users:register_respondent | 200 | 200 | 200 | 200 |
| users:login | 200 | 200 | 200 | 200 |
| users:logout (GET) | 200 | 200 | 200 | 200 |

Not exercised (need an id): `analysis:analytics_dashboard`, `responses:submit_survey_response`, `surveys:edit_survey`, `manage_questions`, `delete_question`, `targeting_criteria`, `delete_survey`, `publish_survey`, `close_survey`.

## AI client
- Host of `HF_SENTIMENT_MODEL_URL`: `router.huggingface.co`. (`.env.example` points at `api-inference.huggingface.co`.)
- Token configured: yes (value not printed).
- "The service was excellent": ERR, `HTTPError 402`.
- Arabic "الخدمة كانت ممتازة": ERR, `HTTPError 402`.
- `huggingface_client.py:54-55` wraps every failure in `ExternalAnalysisServiceError("Hugging Face request failed.")`. The HTTP code is only in `__cause__`.

## Architecture rules
a) ORM in `apps/*/views.py` (`.objects.`, `.save(`, `.delete(`): grep found no matches. Rule holds.

b) Services that write more than one row without `transaction.atomic` (only `question_service.py:61` uses it):
| Method | Evidence |
|---|---|
| ResponseService.submit_response | `response_service.py:67` saves Response, `:78` saves each Answer, `:82` runs analysis (more rows) |
| AuthenticationService.register_respondent | `authentication_service.py:44` saves User, `:53` saves RespondentProfile |
| AnalysisService.analyze_open_text_answers | `analysis_service.py:41` pending result, `:54` update, per answer |
| QuestionService.add_question_options | `question_service.py:95-101` saves options in a loop. Atomic only when called via `add_question_with_options` (`:61`) |

Service calls to the ORM through repositories only. Services contain no direct `.objects.` calls.

c) Known issues:
| ID | Status | Evidence |
|---|---|---|
| K-01 | holds | `response_service.py:67-84`, no atomic block |
| K-02 | holds | `response_service.py:82` calls `analysis_service.analyze_open_text_answers` inside `submit_response`; client timeout 15 s (`huggingface_client.py:23`) |
| K-03 | holds | `targeting_service.py:141` `criteria.region != profile.region` |
| K-04 | cannot verify | CLAUDE.md defines K-01, K-02, K-03, K-06 only. K-04 is not defined anywhere I read |
| K-06 | holds | `git status --ignored` shows `!! docs/` |

## Service inventory
Roles come from the `_ensure_*` guards. "none" = no role check inside the service.
| Service.method(params) -> returns | Roles | Purpose |
|---|---|---|
| AuthenticationService.register_service_provider(name, email, password) -> User | public | Register provider |
| AuthenticationService.register_respondent(name, email, password, age, gender, region, interests) -> User | public | Register respondent and profile |
| AuthenticationService.authenticate_user(email, password) -> User | public | Verify credentials, reject suspended/deleted |
| ProfileService.get_profile(respondent_user) -> profile | RESPONDENT | Read demographic profile |
| ProfileService.update_profile(respondent_user, age, gender, region, interests) -> profile | RESPONDENT | Create or update profile |
| SurveyService.create_survey(provider_user, title, description) -> Survey | SERVICE_PROVIDER | Create draft |
| SurveyService.update_survey(provider_user, survey_id, title, description) -> Survey | SERVICE_PROVIDER (owner) | Edit draft |
| SurveyService.delete_survey(provider_user, survey_id) -> result | SERVICE_PROVIDER (owner) | Delete draft or closed survey |
| SurveyService.publish_survey(provider_user, survey_id) -> Survey | SERVICE_PROVIDER (owner) | Publish after questions and targeting check |
| SurveyService.close_survey(provider_user, survey_id) -> Survey | SERVICE_PROVIDER (owner) | Close published survey |
| SurveyService.list_provider_surveys(provider_user) -> list | SERVICE_PROVIDER | List own surveys |
| SurveyService.get_provider_survey(provider_user, survey_id) -> Survey | SERVICE_PROVIDER (owner) | Ownership check for analytics |
| SurveyService.list_provider_survey_items(provider_user) -> list | SERVICE_PROVIDER | Surveys with action flags |
| SurveyService.get_eligible_surveys(respondent_user) -> list | RESPONDENT | Published, unanswered, targeted surveys |
| QuestionService.add_question(provider_user, survey_id, text, question_type, is_required, order_index) -> Question | SERVICE_PROVIDER (owner, draft) | Add question |
| QuestionService.add_question_with_options(provider_user, survey_id, text, question_type, is_required, order_index, options=None) -> Question | SERVICE_PROVIDER (owner, draft) | Question plus options, atomic |
| QuestionService.add_question_options(provider_user, question_id, options) -> list | SERVICE_PROVIDER (owner, draft) | Add choices |
| QuestionService.update_question(provider_user, question_id, text, is_required, order_index) -> Question | SERVICE_PROVIDER (owner, draft) | Edit question |
| QuestionService.delete_question(provider_user, question_id) -> result | SERVICE_PROVIDER (owner, draft) | Delete question |
| QuestionService.get_response_form_questions(survey_id) -> list | none | Ordered questions for answer form |
| QuestionService.get_survey_question_rows(provider_user, survey_id) -> list | SERVICE_PROVIDER (owner) | Question management rows |
| TargetingService.save_criteria(provider_user, survey_id, gender=None, age_min=None, age_max=None, region=None) -> criteria | SERVICE_PROVIDER (owner, draft) | Create or update targeting |
| TargetingService.match_respondent_to_survey(respondent_user, survey_id) -> bool | RESPONDENT (else False) | Eligibility match |
| TargetingService.get_criteria_initial(provider_user, survey_id) -> dict | SERVICE_PROVIDER (owner) | Prefill targeting form |
| ResponseService.submit_response(respondent_user, survey_id, answers) -> Response | RESPONDENT | Validate and store answers, trigger analysis |
| ResponseService.validate_duplicate_response(respondent_user, survey_id) -> bool | none | True if already answered |
| ResponseService.get_answered_surveys(respondent_user) -> list | RESPONDENT | Answered survey history |
| AnalysisService.analyze_open_text_answers(response_id) -> list | none | Sentiment per open-text answer |
| AnalysisService.get_survey_results(survey_id) -> dict | none | Sentiment counts and per-question summaries |
| AdminService.activate_account(admin_user, user_id) -> User | ADMIN | Activate account |
| AdminService.suspend_account(admin_user, user_id) -> User | ADMIN (not self) | Suspend account |
| AdminService.delete_account(admin_user, user_id) -> User | ADMIN (not self) | Soft-delete account |
| AdminService.list_users(admin_user) -> list | ADMIN | All users |
| AdminService.list_user_management_items(admin_user) -> list | ADMIN | Users with action flags |
| AdminService.generate_system_report(admin_user, date_from, date_to) -> dict | ADMIN | Platform metrics and chart rows |

## Files not on GitHub
`git status --short --ignored`: `.env` (correctly ignored), a Word lock file `Smart_Survey_Project_Documentation/~$art_...docx` (ignored), and `docs/`.
- Tracked files under `docs/`: 0. Ignored files under `docs/`: 79.
- Non-Markdown project material inside `docs/`:
| File | Bytes |
|---|---|
| docs/diagrams/site_map.puml | 5,242 |
| docs/fixed_use_case_assets/use_case_specifications_en_corrected.html | 32,788 |
| docs/legacy_input/use_case_specifications_en_no_priority.html | 53,474 |
| docs/legacy_input/class_diagram.mmd | 9,949 |
| docs/legacy_input/erd.mmd | 2,701 |
| docs/committee_training_ar/دليل_الدفاع_التقني_اللجنة.docx | 136,122 |
| docs/explanation/شرح_كود_مشروع_منصة_استبيانات_الآراء_الذكية.docx | 58,734 |
- Markdown: 15 Arabic committee-training files (`docs/committee_training_ar/01..15`, 3.4-13 KB each), `docs/explanation/*.md` (42,857), `docs/legacy_input/‏‏activity diagram plantuml - Engish.md` (24,329), plus the English audit, context, requirements and report notes.
- No images, `.drawio`, `.mdj`, `.vsdx`, `.pdf` or `.pptx` files outside `.venv`.

## Findings
| ID | Severity | Evidence | Suggested fix |
|---|---|---|---|
| F-01 | High | K-01: `response_service.py:67-84` writes Response, Answers and runs analysis with no atomic block | Wrap writes in `transaction.atomic` in the service; move analysis out (F-03) |
| F-02 | High | `authentication_service.py:44,53` saves User then Profile non-atomically; a failure leaves a respondent without a profile | Wrap `register_respondent` in `transaction.atomic`; add a test |
| F-03 | High | K-02: `response_service.py:82` runs HF calls inside `submit_response`; each call can wait up to 15 s | Run analysis after commit (task queue or `transaction.on_commit`) |
| F-04 | High | `docs/` has 79 ignored files, 0 tracked; includes 2 `.docx`, 2 `.html`, `.puml`, 2 `.mmd` | Fix `.gitignore` (K-06) or move the files to a tracked folder; commit on a separate branch |
| F-05 | High | AI call fails: `HTTPError 402` for English and Arabic on `router.huggingface.co`. In the service the failure becomes `mark_failed()` (`analysis_service.py:51-52`) with no visible error | Resolve the HF account or credits, or choose a pretrained model route that works; surface the HTTP status in the error |
| F-06 | Medium | DB port mismatch: compose publishes 5433 (`docker-compose.yml:11`), `.env` and `.env.example:8` use 5432; 5432 is served by a container outside compose. Session start: tests errored with `OperationalError` | Make compose publish 5432 (or change `.env`/`.env.example` to 5433) and remove the legacy container |
| F-07 | Medium | `analysis_service.py:41,54` writes several rows per call without atomic; `question_service.py:95-101` loops saves without atomic outside `add_question_with_options` | Add atomic in the service methods |
| F-08 | Medium | K-03: `targeting_service.py:141` exact string comparison on free text | Normalize region (trim, casefold) or use a controlled list |
| F-09 | Medium | Ownership check lives in the view: `apps/analysis/views.py:16` calls `get_provider_survey`, while `AnalysisService.get_survey_results` and `QuestionService.get_response_form_questions` check no role (`apps/responses/views.py:99`) | A REST API must reuse a service method that checks role and ownership; add one |
| F-10 | Medium | Wrong role gets `302 /users/login/` (smoke test), not 403 | API layer must return 401/403 JSON |
| F-11 | Medium | `flutter --version` hung twice (120 s, 90 s); Flutter toolchain unverified | Run `flutter doctor` manually and fix before client work |
| F-12 | Medium | CLAUDE.md lists K-01, K-02, K-03, K-06 only; Task 02 asks about K-04 | Define K-04 in CLAUDE.md or drop it from the task |
| F-13 | Low | Report claims 163 tests; actual: 168 collected, 165 defs; parametrize at `test_profile_service.py:123` explains 168 vs 165 only | Update the report to 168 |
| F-14 | Low | `repositories/user_repository.py` defines `save` twice (lines 10 and 27) | Delete the duplicate |
| F-15 | Low | `config/settings.py:11` falls back to `SECRET_KEY="replace-this-secret-key"` | Fail startup if `SECRET_KEY` is unset in non-debug mode |
| F-16 | Low | `GET users:logout` returned 200 for all four roles | Confirm logout is POST-only |
| F-17 | Low | `huggingface_client.py:54-55` hides the HTTP status in `__cause__` | Include the status code in the exception |
