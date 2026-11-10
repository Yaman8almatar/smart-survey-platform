# Increment 1 pre-release audit (TASK-21, completed by TASK-21B)

| Item | Value |
|---|---|
| Date | 2026-11-10 (parts written 2026-11-08, Blockers re-checked 2026-11-10) |
| Target | develop @ b77dbb3 (base main @ 1356167), release v1.2-increment1, committee review 2026-11-15 |
| Mode | Read-only on the repository. No test suite, no app run, no database query, no HTTP call to localhost. |
| Method | TASK-21 wrote Parts 1 to 5 and Part 7 from the code at b77dbb3. TASK-21B re-read the code cited by each of the 9 Blockers, plus the lines needed to follow the call path, and gave each one a mark. |
| Verified | The 9 Blockers only. Mark: Verified (the cited code does what the finding says), Downgraded (new severity and why) or Rejected (why), each with the file:line read. |
| Not verified | Every Should and Later finding is copied as written and is **not verified**. |
| Not reached | Part 6 (documentation drift) and Part 8 (release pull request draft): not reached, by decision D-129. Part 7 section (c) was left "to be completed after verification" and is not filled in here. |
| Access notes | Part 1 read the old BRIEF.md and checks.md under docs/audit/ and once listed docs/audit/ with Glob after a refused `ls`, before the correction that denies docs/** arrived (Part 1 header). Part 5 ran a helper script on the pure mapping functions of migration 0004 and then deleted it (Part 5 header). No line of backend/.env was read, by the parts or by TASK-21B. No secret value appears in this report. |
| Allowed checks | `manage.py check --deploy`: exit 0, 6 warnings (W004, W008, W012, W016, W018 DEBUG is True, W020 ALLOWED_HOSTS empty; local .env in effect). `makemigrations --check --dry-run`: no changes. Run 2026-11-08, not re-run. |

## Summary after verification

Counts by part and severity. The numbers count findings as the parts wrote them; the UC-06 defect is counted once per part that found it.

| Part | Blocker | Should | Later | Scope | Total |
|---|---|---|---|---|---|
| 1 Traceability | 4 | 9 | 9 | 0 | 22 |
| 2 API security and correctness | 0 | 7 | 10 | 0 | 17 |
| 3 API contract | 1 | 4 | 11 | 0 | 16 |
| 4 App | 1 | 8 | 16 | 0 | 25 |
| 5 Data and history | 2 (was 3) | 8 (was 7) | 12 | 0 | 22 |
| **All** | **8 (was 9)** | **36 (was 35)** | **58** | **0** | **102** |

Distinct Blockers after merging duplicates and verification: **6** (A-01, A-15, A-16, A-20, A-204, A-209). A-203 was downgraded to Should. No Blocker was rejected.

## Blockers with verification marks

A-100 (Part 3) and A-150 (Part 4) describe the same defect as A-01 (Part 1) and are merged under A-01.

| ID | Part | Title | Mark | Code read (file:line at b77dbb3) | Reason |
|---|---|---|---|---|---|
| A-01 (= A-100, A-150) | 1, 3, 4 | UC-06 answered surveys missing from the app | **Verified** | frontend/lib/features/surveys/surveys_repository.dart:6-25; frontend/lib/features/surveys/eligible_surveys_screen.dart:134-158; backend/apps/api/urls.py:24; backend/apps/api/views.py:362-371; backend/apps/responses/urls.py:15; search of frontend/lib for `me/responses` and `answered` | SurveysRepository has one method, `eligibleSurveys`, calling only `surveys/eligible/`. No file in frontend/lib calls `me/responses/`. The app bar has only profile and log out. The API (`AnsweredSurveysView`) and the web (`answered-surveys/`) both have the feature. FR-01 "covering everything the current respondent web pages offer" is false today. |
| A-15 | 1 | Colour literals outside the token files (issue 61) | **Verified** | backend/static/js/site.js:136,147,155,162,309,310,422; backend/apps/analysis/templates/analysis/analytics_dashboard.html:244,245,289,290; backend/templates/base.html:31,208; issue 61 body | Every cited line holds a hex colour literal. Issue 61 has the box "No colour literal outside frontend/lib/theme and backend/static/css/tokens.css" ticked. Cheap to fix; a Blocker only by the "false Done claim" rule, not because it breaks the demo. |
| A-16 | 1 | Labels not in sentence case (issue 61) | **Verified** | backend/apps/responses/templates/responses/respondent_dashboard.html:74,92,110; eligible_surveys.html:43; backend/apps/surveys/templates/surveys/provider_dashboard.html:20,24,98,107; survey_list.html:73,82; backend/apps/admin_panel/templates/admin_panel/admin_dashboard.html:33,53; issue 61 body | All 14 lines are title case ("Manage Demographic Profile", "Start Survey", "User Management" and others). Issue 61 has "labels are sentence case" ticked. Same rule note as A-15. |
| A-20 | 1 | FR-01, FR-02, FR-06 counted Done without diagrams and report | **Verified** | planning/STATUS.md:12; planning/KANBAN.md:34,37-39; `git log` of diagrams/ (last 62e7ac0, 2026-10-29) and documentation/graduation-1/ (last 1356167, 2026-10-30); `git ls-files diagrams` | The Definition of Done requires "affected diagrams updated" and the report section. diagrams/ holds four PNGs and a README, no PlantUML source and no ER diagram; both folders last changed before c762367 (2026-11-07, FR-02 fields) and b3d9928 (2026-11-08, draft table). Issues 15, 16 and 20 are still OPEN, so the false claim is in STATUS.md and the board policy, not yet on GitHub. Report content was not read. |
| A-203 | 5 | Database seeded before 0004 loses the demo region | **Downgraded to Should** | backend/apps/core/migrations/0004_map_profile_lists.py:43-64,114-116,134-148; seed_demo_data.py:116-127,148-158; `git show c762367^:…/seed_demo_data.py` | The code does what the finding says: "Amman" (the old seed value) is in no alias list, so 0004:138 sets the profile region to "" and 0004:147 sets the targeting region to NULL. But the effect needs a database state nobody has confirmed, and the current seed is an idempotent upsert that writes DAMASCUS to both (seed:123,156). One seed run repairs it, and that run is already part of the A-204 fix. It is a pre-demo checklist item, not a code Blocker. |
| A-204 | 5 | The only seeded survey is already answered, so the app list is empty | **Verified** | backend/apps/core/management/commands/seed_demo_data.py:57-89,191-197; backend/repositories/survey_repository.py:25-28,61 | The seed creates one published survey and a response to it by respondent@demo.com (seed:81). The eligible query excludes surveys with a response by that respondent (`.filter(~Exists(has_responded))`, :61). On seeded data the respondent sees an empty list, so the answer and draft flows cannot be shown without creating another survey first. |
| A-209 | 5 | Sentiment silently FAILED if Hugging Face refuses | **Verified** (condition still unconfirmed) | backend/services/analysis_service.py:53-62; backend/infrastructure/huggingface_client.py:36-64; backend/.env.example:15 (host only, not backend/.env) | Any HTTP error, 402 included, becomes ExternalAnalysisServiceError (client:57-62), which the service turns into `result.mark_failed()` (:61-62) with only a log warning. FAILED results are skipped in the counts (:82-84), so the dashboard shows zero sentiment with no visible error. .env.example:15 still names the older api-inference host. Whether the current credentials work could not be checked; one real call before the demo settles it. |

---

# Parts as written by TASK-21

Below this line the parts are copied unchanged from the TASK-21 notes. Should and Later findings in them are not verified. A-203 appears there with its original severity; its mark is in the table above.

# TASK-21 audit, Part 1: traceability

Target: develop @ b77dbb3. Findings A-01 to A-22. No test suite was run, so "test" below means a test that exists and whose content or name proves the point. Whether it passes today was not checked.

## Header

**Read:** planning/API.md, STATUS.md, KANBAN.md; backend/apps/responses (urls, views, forms, all six templates); backend/apps/api (all); backend/services (response, profile, authentication, targeting, survey, question, admin in full; analysis by search); repositories for responses, drafts, users, surveys; models for profile, user, response, draft; config/settings.py; core/enums.py; every file in frontend/lib except answer_option.dart and interest_icons.dart, which were seen only through search; frontend/pubspec.yaml; Android manifests; docker-compose files; test names in frontend/test and backend/tests, with the suspension, race and throttling tests read in full. Issues 15, 16, 20, 35, 38, 48, 49, 61 and PR bodies 55, 57, 60 through gh.

**Not reached:**
- The GitHub Projects board. KANBAN.md holds only the workflow policy and no card states, and the brief allows only the listed `gh issue view` fields. So "does the KANBAN status agree" is answered against the policy only.
- CI run results. They need a gh command outside the brief. CI claims are marked as reported by the PR body.
- The review database of issue 48 (no database access).
- The report .docx content. Only its last commit date was read.
- No app was run. Everything here is from reading the code.

**Access note:** The correction that denied `docs/**`, `backend/.env` and `.venv/**` arrived during the work. Before it arrived, this audit read `docs/audit/BRIEF.md` and `docs/audit/checks.md`, listed `docs/audit` with Glob, and read three simplejwt source files under `.venv` (authentication.py, serializers.py, settings.py) and ran `pip show` from `.venv`. `backend/.env` was never opened. Nothing was written under `docs/`. Those `.venv` files were not reopened after the correction and are not quoted here. The two statements that depend on them are marked "library behaviour" in table (c); the refresh half is also proved by a repository test, and the access-token half is not (see A-10).

## (a) Respondent web pages against the app

| Web page | What the web offers | App screen (file:line) | API call | Verdict |
|---|---|---|---|---|
| respondent_dashboard | Profile completion Complete/Incomplete (template:43-48); eligible count (:53-54); links to profile, eligible, answered (:15-35, :69-111) | No dashboard. Nearest is EligibleSurveysScreen as home, `frontend/lib/features/surveys/eligible_surveys_screen.dart:134`. Profile link :138-142 | `surveys/eligible/` (surveys_repository.dart:12) | **Partial.** Completion status and count are not on the home screen; the answered link does not exist. A-01, A-02 |
| demographic_profile | Age, gender, governorate, interests with errors; Back; Save; success message (template:25-93) | ProfileScreen, `features/profile/profile_screen.dart:54`; save :210; Profile saved :230; back with discard dialog :292 | `GET/PUT me/profile/`, `profile/options/` (profile_repository.dart:13,21,31) | **Full**, and adds three fields and the percent |
| eligible_surveys | Title, status badge, description or "No description", Start Survey, Dashboard link, empty message (template:30-52) | EligibleSurveysScreen :163-224, card :262-317 | `surveys/eligible/` | **Partial, minor.** Status badge and "No description" are replaced or dropped. A-03 |
| answered_surveys | Survey number, title, Already submitted badge, description, submitted date, links, empty message with link (template:32-73) | **Missing** | `GET /me/responses/` exists (apps/api/urls.py:24) but is never called | **Missing.** A-01 |
| submit_survey_response | Title; question text, type and required labels; textarea, rating select, radios; Back; Submit; "No questions are available" (template:9-98) | SurveyStartScreen `features/answer/survey_start_screen.dart:17`, SurveyAnswerScreen `survey_answer_screen.dart:27` | `surveys/{id}/`, `surveys/{id}/responses/`, draft calls (answer_repository.dart:15,21,33,43,47) | **Full.** Type label becomes a hint (:418-422), required shows as the absence of an Optional tag (:442-445). The no-questions message is absent but unreachable (A-08) |
| submission_confirmation | Response received text; links to eligible and dashboard (template:15-33) | SurveySentScreen `survey_sent_screen.dart:18`, Back to surveys :158-161 | Uses the 201 receipt | **Full.** The dashboard link has no target because there is no dashboard |

**Advisor's UC-06 statement: CONFIRMED.** A case-insensitive search of frontend/lib for `me/responses|answered|getAnswered|AnsweredSurvey|history` finds no `me/responses` path, no repository method and no screen. Every hit is an unrelated word: draft counts, the "You already answered" block, a comment. frontend/test has no such call either. SurveysRepository has the single method `eligibleSurveys` (surveys_repository.dart:11). The API side works: apps/api/views.py:362-371, test `test_history_lists_only_own_responses` (tests/api/test_responses.py:226).

## (b) Requirements and issues, criterion by criterion

### FR-01 (Must)

| UC / criterion | Status | Evidence | Tests |
|---|---|---|---|
| Flutter respondent app runs on a phone | Partial | Android exists; default base URL api_config.dart:7. Never run on a device (A-18) | no test |
| Secure login | Met | login_screen.dart:66; JWT; SecureTokenStore token_store.dart:13; refresh on 401 api_client.dart:60-64 | `success stores tokens and opens the eligible list`, `401 -> refresh -> retry succeeds with the new token`. SecureTokenStore itself: no test |
| Everything the web pages offer | **Missing** | Table (a) | A-01, A-02 |
| UC-01 screen reachable from login | Met | login_screen.dart:115,228 | `the login screen links to Create account` |
| UC-01 sends account and profile | Met | register_screen.dart:109-117; auth_repository.dart:49 | `success sends codes, logs in with the same credentials and ...` (register_screen_test:187) |
| UC-01 account and profile stored together | Met | authentication_service.py:62-73 | `test_respondent_registration_rolls_back_user_when_profile_save_fails` |
| UC-01 validation, client and server | Met | register_screen.dart:83-98; serializers.py:86-99 | `empty form is blocked without calling the API`, `age outside 1 to 120 is blocked`, `a server field error appears under the matching field`, `test_register_rejects_invalid_field` |
| UC-01 same fields as the web form | Partial | No confirm password (A-21) | no test |
| UC-02 read profile | Met | profile_screen.dart:108-129 | `loads, then shows the ring, hero copy and stored values`, `test_profile_get_returns_demographics` |
| UC-02 edit and save | Met | profile_screen.dart:198-260 | `save sends all seven fields and shows the new percent`, `test_profile_put_updates_and_persists` |
| UC-02 first time, no profile | Met | profile_repository.dart:23; profile_hero.dart:58-64 | `first time shows 0% and a disabled Save profile`, `test_profile_put_creates_missing_profile` |
| UC-03 list matches profile, published, not answered | Met | survey_repository.py:50-65 | `test_eligible_lists_matching_survey_with_question_count`, `test_eligible_excludes_surveys_that_do_not_match_the_profile`, `test_eligible_excludes_unpublished_surveys`, `test_eligible_excludes_already_answered_surveys` |
| UC-03 show and open a survey | Met | eligible_surveys_screen.dart:102-114,262-317 | `shows title, description and question count, no Start`, `the card opens the start screen, the list reloads on return` |
| UC-04 all three question types | Met | survey_answer_screen.dart:470-505; answer_repository.dart:56-65 | `sends each answer type under its own key` |
| UC-04 send and confirm | Met | survey_answer_screen.dart:172-207 | `Send posts the body and shows Answers sent`, `test_submit_stores_response_and_answers` |
| UC-04 refused cases shown clearly | Met | survey_parts.dart:47-74 | `409 duplicate_response shows its message`, `409 not_editable while sending says so`, `$code while loading replaces the screen` |
| UC-05 | Out of Increment 1 | Brief | n/a |
| UC-06 view answered surveys | **Missing** | A-01 | API only: `test_history_lists_only_own_responses`. App: no test |

### FR-02 (Must)

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Education is a fixed list, server enforced | Met | enums.py:64; serializers.py:59; profile_service.py:15-19,106-112 | `test_profile_put_rejects_invalid_field`, `test_invalid_profile_field_is_rejected` |
| Occupation fixed list | Met | enums.py:76; serializers.py:62; profile_service.py:17 | same |
| Marital status fixed list | Met | enums.py:90; serializers.py:63; profile_service.py:18 | same |
| Governorate fixed list | Met | enums.py:44; serializers.py:36; profile_service.py:96; web form forms.py:27; targeting targeting_service.py:118 | `test_register_rejects_free_text_region_and_interests`, `test_governorates_end_with_outside_syria`, `a 400 region error appears under Governorate` |
| Interests fixed list, distinct, at least one | Met | serializers.py:40-53; profile_service.py:114-126 | `test_all_twelve_interests_are_accepted`, `test_invalid_profile_field_is_rejected` |
| Lists enforced at database level | Not required | `choices` on the model is not a database check (respondent_profile.py:38-55). All write paths go through ProfileService or AuthenticationService, so the service rule holds | n/a |
| App picks only from the lists | Met | choice_select_field.dart:35-69; interest_chips.dart:41; lists from API profile_repository.dart:13 | `options parses every list and sends no token`, `validation blocks the request and counts the fields` |
| Completion percent counts the right fields | Met | respondent_profile.py:21-29,109-112: seven details, each counted once; PREFER_NOT_TO_SAY counts; blank region does not. Matches API.md:63-65 | `test_completion_percent_counts_seven_details`, `test_profile_get_returns_optional_fields_and_completion` |
| Percent shown in the app | Met | profile_hero.dart:148-157; signal_ring.dart:143 | `100% shows the Complete badge`, `save sends all seven fields and shows the new percent` |
| Percent is server computed | Met | serializers.py:66 read only; profile_models.dart:82-90 sends no percent | `save sends a PUT with all seven fields` |
| Web has the new fields and percent | Missing | A-22 | no test |

### FR-06 (Should)

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Position ring (D-118) | Met | survey_answer_screen.dart:369-375 | `the first question shows Next only` (asserts `1/3`), `the last question ring has no ping` (asserts `3/3`) |
| Required validation, client | Met | :143-148 blocks every forward move, so the review cannot be reached with a required blank. `_send` has no check of its own, and none is needed | `Next without a required answer shows the error and stays`, `a required text of spaces counts as no answer` |
| Required validation, server | Met | response_service.py:82,249-259,310-357 | `test_missing_required_answer_is_rejected`, `test_submit_without_required_answer_returns_400` |
| Server refusal shown in the app | Met | survey_answer_screen.dart:216-223 | `400 marks the answer named by its position`, `400 naming no question shows the API message` |
| Optional skip | Met | :510-514,534-539; server response_service.py:272 | `Skip on an optional question moves on`, `an optional empty last question still shows Review answers`, `shows the answers and Skipped`, `test_submit_accepts_missing_optional_answer` |
| Save draft on the server | Met | :90,94-128,253; response_service.py:132-163. Saved on question change and on leaving, not while typing (A-19) | `Next sends one PUT with the answers`, `one save at a time; the newest answers follow`, `typing sends nothing until the question changes`, `test_put_returns_the_stored_shape`, `test_second_save_replaces_answers_and_keeps_started_at` |
| Resume later | Met | survey_start_screen.dart:49-60,101-106 | `a draft shows the resume view`, `Continue opens the first unanswered question`, `Continue opens the review when all are answered` |
| Start over | Met | :108-153 | `Start over then confirm deletes and opens question 1 empty`, `Start over then Cancel keeps the draft` |
| Resume after app restart | Met by trace | Tokens persist (token_store.dart:13), app.dart:66-75 reopens the list, the start screen reads the draft from the server. On `flutter run -d chrome` the port is random unless fixed, so browser storage is lost and the user logs in again; the draft is still there. The list shows no sign that a draft exists | Each link has a test (`a valid stored session opens the eligible list`, `a draft shows the resume view`). No test runs the whole path, and it was never run by hand (A-17) |
| Draft removed at submit | Met | response_service.py:106 | `test_submit_with_draft_deletes_it_and_copies_started_at`, `test_submit_deletes_the_draft_and_get_returns_409` |

### Issue 15, OPEN. Boxes unticked. KANBAN policy: an issue closes at release, so OPEN is consistent.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Login, register, profile, eligible, answer screens use the API | Met | Table (a) | See FR-01 |
| Answered-surveys screen uses the API | **Missing** | A-01 | no test |
| Tokens stored securely | Met | token_store.dart:13-41 | no test of SecureTokenStore |
| Refreshed on 401 | Met | api_client.dart:60-99 | `401 -> refresh -> retry succeeds with the new token`, `two parallel 401s trigger exactly one refresh call`, `failed refresh clears the tokens and throws SessionExpired` |
| Every screen has loading, error, empty | Partial | Table (c), A-07, A-08 | Table (c) |
| DoD tests in CI | Not read | CI not reached | n/a |
| DoD diagrams updated | Missing | `diagrams` last changed 2026-10-29, commit 62e7ac0; A-20 | n/a |
| DoD report section | Missing | Report last changed 2026-10-30, before this work; A-20 | n/a |

### Issue 16, OPEN. Boxes unticked. Consistent with policy.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Governorate fixed, no free text | Met | FR-02 table; migrations 0004, 0005 | `test_register_rejects_free_text_region_and_interests` |
| API validates choices | Met | FR-02 table | `test_profile_put_rejects_invalid_field` |
| App validates choices | Met | profile_screen.dart:171-187 | `validation blocks the request and counts the fields` |
| Profile shows percent | Met | profile_hero.dart:153-157 | `100% shows the Complete badge` |
| Story: "so that I receive surveys that match me" | Partial | Only age, gender, governorate are used. A-09 | no test |
| DoD diagrams, report | Missing | A-20 | n/a |

### Issue 20, OPEN. Boxes unticked. STATUS.md:12 calls it Done after merge. KANBAN.md:34,37 requires the DoD for Done, and the DoD is not met: A-20.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Required block submission with a message | Met | FR-06 table; messages survey_answer_screen.dart:423-425 | `Next without a required answer shows the error and stays` |
| Optional can be skipped | Met | FR-06 table | `Skip on an optional question moves on` |
| Draft saved on the server, resumed later | Met | FR-06 table | `Next sends one PUT with the answers`, `a draft shows the resume view` |
| DoD diagrams, report | Missing | A-20 | n/a |

### Issue 35, OPEN. Boxes ticked. Consistent with policy.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Parallel duplicates return 409 | Met | Trace in (c) | `test_parallel_duplicate_submit_returns_409` |
| A test reproduces the race | Met | Two threads with a barrier on a real database | `test_parallel_submits_store_one_response` (tests/services/test_response_service.py:616) |
| Docs agree | No | API.md:186 still says 500. A-13 | n/a |

### Issue 38, OPEN. Boxes ticked. Consistent with policy.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| ScopedRateThrottle, one scope per endpoint, rates in settings | Met | settings.py:126-132; views.py:49,76,98,125 | `test_request_after_the_limit_is_throttled` |
| 429, Retry-After, standard shape | Met | exceptions.py:42-55 | same test asserts all three |
| 429 after the limit, normal below | Met | | `test_requests_up_to_the_limit_get_their_normal_answer`, `test_using_up_login_does_not_block_token_refresh` |
| Cache configured, shared if several processes | Met, conditional | settings.py:140-147 uses Redis only if REDIS_URL is set; the prod compose has Redis (docker-compose.prod.yml:26). The value lives in an env file outside the repository. The demo is one process | no test |
| Documented in API.md | Met | API.md:158-178 | n/a |

### Issue 48, OPEN. Boxes ticked. Consistent with policy.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Compose: one service, db, port 5432 | Met | docker-compose.yml:2,11 (file read; `docker compose config` not run) | n/a |
| Prod compose: no secret, no beat | Met | docker-compose.prod.yml:7 uses env_file; services are db, redis, web, worker | n/a |
| No production code checks for tests | Met | Search of backend outside tests finds only manage.py:11 | n/a |
| Probes not throttled, no exception text | Met | apps/core/views_health.py:9-24 | `test_health_probes_are_not_throttled`, `test_readiness_probe_returns_503_without_exception_text` |
| Flutter logout calls auth/logout/ | Met | auth_repository.dart:87-91 | auth_repository_logout_test.dart:13, `a 400 from the server still clears both tokens` |
| Review worktree removed | Met | `git worktree list` shows one entry | n/a |
| Review database removed | Not verified | No database access | n/a |

### Issue 49, OPEN. Boxes ticked. Consistent with policy.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| Django 5.2.x pinned | Met | backend/requirements.txt:1 | n/a |
| CI green | Not read | PR 55 body reports local checks | n/a |
| makemigrations --check clean | Met | checks.md:13-14 | n/a |
| Smoke checks pass | Met as reported, with gaps | PR 55 body: web admin, provider, Flutter web and API smoke. Analytics page and response submit were not run | n/a |
| Deprecation warnings named | Met | PR 55 body: none | n/a |

### Issue 61, OPEN. Boxes ticked. T-8 is outside KANBAN.md:19, which lists T-1..T-7.

| Criterion | Status | Evidence | Tests |
|---|---|---|---|
| No colour literal outside the two allowed places, app | Met | Search for `\bColor\(0x\|\bColors\.` outside lib/theme: none | n/a |
| No colour literal, web | **Missing** | A-15 | n/a |
| App bars and navbar brand-deep | Met | app_theme.dart:106; site.css:79 | `app bars use the brand-deep band` |
| Labels sentence case | **Missing** on the web | A-16. App labels are sentence case | n/a |
| Cards have no shadow | Met | app_theme.dart:116; `--ssp-shadow-sm: none` site.css:22 | `buttons use radius 12 and the snackbar radius 6` covers radii only |
| Reduced motion | Met | tokens.dart:126-129; tokens.css:89-96 | `with animations disabled a question changes at once`, `with animations disabled the final values show at once` |
| CI green with counts | As reported | PR 60 body says 505 backend tests passed. PR 57 body says 48 Flutter tests, while the issue says 49. CI not read | n/a |

## (c) Non-functional requirements

### NFR-05, screen by screen

"Missing (n/a)" means the screen has no such state and nothing to show in it. The requirement's wording still says every screen.

| Screen | Loading | Error | Empty | Tests |
|---|---|---|---|---|
| AuthGate, app.dart:43 | Met :94 | **Missing**: failure falls through silently to login, :76-78 (A-07) | Missing (n/a) | `no stored session opens login after a progress indicator`, `a stored session the server rejects opens login`. Server down: no test |
| LoginScreen | Met, button spinner login_screen.dart:217-224 | Met :94-113,210-213 | Missing (n/a); blank form blocked :175,206 | `wrong password shows the credentials message`, `an unreachable server shows the network message`, `empty fields are blocked without calling the API`. Spinner: no test |
| RegisterScreen | Met :162-164,357-364 | Met :176-195,350-353 | Missing (n/a) | `options that fail to load show a retry`, `an unreachable server shows the network message` |
| EligibleSurveysScreen | Met :166-168 | Met :169-183 | Met :186-206 | `shows a progress indicator while loading`, `shows the error with Try again, and Try again reloads`, `shows the empty state` |
| ProfileScreen | Met skeleton :321; profile_hero.dart:260 | Met :322-327,700-740 | Met profile_hero.dart:58-64 | `a load error shows Try again, and a retry succeeds`, `first time shows 0% and a disabled Save profile`. Skeleton: `with animations disabled the final values show at once` |
| SurveyStartScreen | Met :166-169 | Met :170-180 | Missing, zero questions (A-08) | `shows progress while the detail loads`, `a network failure offers Try again, which reloads` |
| SurveyAnswerScreen | Met for send and leave :343-352,673-683 | Met :209-239 | Missing, zero questions (A-08) | `while sending: one request, disabled rows, no leaving`, `a network failure shows the snackbar and keeps the answers` |
| SurveySentScreen | Missing (n/a); no load | Missing (n/a) | Missing (n/a) | n/a |
| Answered surveys | **No screen** (A-01) | | | |

### NFR-05, language and font

| Criterion | Status | Evidence |
|---|---|---|
| English UI | Met | All strings in English; no localisation package in pubspec.yaml |
| Arabic-capable fonts | **Partial** | No font asset is bundled: pubspec.yaml:56-61 has no fonts section and `frontend/assets` does not exist; fonts come from google_fonts at run time (:37). Readex Pro has an Arabic subset. IBM Plex Sans does not: Google Fonts CSS lists cyrillic, cyrillic-ext, greek, latin, latin-ext, vietnamese only. IBM Plex Sans is the font of body, heading, label and caption (app_theme.dart:35-57), so question text, options and answers. A-04, A-05 |
| Test | No test checks a font |

### NFR-02

| Item | Status | Evidence | Tests |
|---|---|---|---|
| JWT for the mobile API | Met | settings.py:122-124,150-159 | `test_token_returns_access_and_refresh`, `test_anonymous_gets_401_in_error_shape`, `adds the Bearer header when an access token exists` |
| Role checks in the business layer | Met | `_ensure_respondent` in response_service.py:218, profile_service.py:132, survey_service.py:195; question_service.py:185. Gate also at permissions.py:6. `/me/` has only the gate and returns only the caller's own data | `test_non_respondent_cannot_submit_response`, `test_draft_operation_rejects_provider`, `test_other_roles_get_403` |
| Ownership checks in the business layer | Met | Queries are scoped by user id; survey_service.py:177-188. K-12 fixed: apps/analysis/views.py:16 calls the service | `test_history_lists_only_own_responses`, `test_draft_operation_rejects_ineligible_respondent` |
| Account status rule in the business layer | Partial | Only permissions.py:19 and login; not in services (A-11) | `test_is_respondent_permission_refuses_inactive_account_status` |
| Suspended refused on next request | Met, one test missing | Trace below; A-10, A-11 | Trace below |
| Passwords hashed | Met | authentication_service.py:33,59; serializers.py:91 write only | `test_register_creates_respondent_and_profile_without_tokens` (asserts check_password) |
| Throttling with 429 | Met | Issue 38 table | `test_request_after_the_limit_is_throttled` |

**Suspended account, real path.**
1. AdminService.suspend_account (admin_service.py:29-35) calls User.suspend, which sets `account_status=SUSPENDED` and `is_active=False` (user.py:79-80), and saves.
2. *Still-valid access token:* JWTAuthentication is the only authenticator (settings.py:122-124). Library behaviour, simplejwt 5.5.1 with its default active-user check: an inactive user is refused during authentication with 401. The shared handler returns the standard error shape. The token's remaining 30 minutes do not help. The app then calls refresh (api_client.dart:60-61).
3. *Refresh:* TokenRefresh (views.py:124) has no custom serializer. Library behaviour: the refresh serializer applies the active-user rule and answers 401. Proved by `test_refresh_refuses_account_suspended_after_token_issue` (tests/api/test_auth.py:293). The app clears the tokens and raises SessionExpiredException (api_client.dart:87-90), and screens open login with "Your session ended."
4. *Login afterwards:* refused, authentication_service.py:89-90; the app shows the wrong message (A-12).
5. *Old rows with SUSPENDED and is_active=True:* the access token passes authentication but IsRespondent answers 403 (permissions.py:19). Refresh still succeeds. API.md:189 admits this and no data migration exists (A-11).

### NFR-03

| Item | Status | Evidence | Tests |
|---|---|---|---|
| Multi-row writes atomic | Met | response_service.py:86; authentication_service.py:62; question_service.py:68,102; analysis_service.py:41. K-01 is fixed | `test_submit_response_rolls_back_when_answer_save_fails`, `test_failed_submit_keeps_the_draft`, `test_respondent_registration_rolls_back_user_when_profile_save_fails`, `test_add_question_options_rolls_back_all_options_when_a_write_fails`, `test_analyze_open_text_answers_rolls_back_all_results_when_a_write_fails` |
| One response per respondent per survey, DB constraint | Met | response.py:26-31; migration 0001_initial.py:177 | `test_parallel_submits_store_one_response` |
| Duplicate 409 under parallel submits | Met | Trace below | `test_parallel_submits_store_one_response`, `test_parallel_duplicate_submit_returns_409`, `test_other_integrity_error_is_not_turned_into_duplicate_response`, `test_unknown_integrity_error_returns_500` |

**Duplicate, real path.** Both requests can pass the pre-check at response_service.py:69. Each enters `transaction.atomic()` at :86 and the second insert violates `unique_response_per_survey_respondent`. `ATOMIC_REQUESTS` is not set, so the inner block is the whole transaction. The IntegrityError is caught outside the block (:115), matched by constraint name (:117) and raised as DuplicateResponse (:118). exceptions.py:20 maps it to 409 `duplicate_response`. Another integrity error is re-raised (:119) and becomes 500. The app's send button is guarded by `_sending` (survey_answer_screen.dart:173), and a retry after a lost reply counts as sent (:211-214).

### Known issues, real state at b77dbb3

| ID | State | Evidence |
|---|---|---|
| K-01 | Fixed; CLAUDE.md is stale | response_service.py:86 |
| K-02 | Still open by default. Runs after commit but inside the request unless USE_CELERY is set | response_service.py:111,192; settings.py:215. The app allows 60 seconds, answer_repository.dart:10 |
| K-03 | Fixed in substance: exact compare of fixed codes | targeting_service.py:118,141 |
| K-04 | Open | targeting_service.py:131-143; survey_repository.py:30-48. A-09 |
| K-12 | Fixed; CLAUDE.md is stale | apps/analysis/views.py:16-17 |

## Findings

### A-01
| Field | Content |
|---|---|
| Severity | Blocker |
| Confidence | Confirmed |
| Location | frontend/lib/features/surveys/surveys_repository.dart:11 |
| Quote | `Future<List<EligibleSurvey>> eligibleSurveys() async {` |
| Trigger | A respondent who has submitted a survey looks for it in the app. |
| Effect | There is no answered-surveys screen, no link and no repository method; `GET /me/responses/` has no caller. UC-06 and the issue 15 criterion are unmet, and FR-01 (Must) cannot be claimed as covering the web pages. The advisor's statement is correct. |
| Fix direction | Add a repository method for `me/responses/` and an answered-surveys screen with its three states, reachable from the home screen. |

### A-02
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/surveys/eligible_surveys_screen.dart:136 |
| Quote | `title: Text(widget.user.displayName),` |
| Trigger | A respondent opens the app after login. |
| Effect | The web dashboard's profile completion status and eligible count have no equivalent on the home screen. Completion appears only after opening the profile. |
| Fix direction | Show profile completion and the count on the home screen, or record that the list replaces the dashboard. |

### A-03
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/surveys/eligible_surveys_screen.dart:287 |
| Quote | `const MatchBadge(),` |
| Trigger | A survey card is shown, or a survey has no description. |
| Effect | The web's status badge and "No description" text are absent. Little is lost, since only published surveys are listed. |
| Fix direction | Record it as an intended difference. |

### A-04
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/theme/app_theme.dart:41 |
| Quote | `static TextStyle get body => GoogleFonts.ibmPlexSans(` |
| Trigger | A survey has Arabic question text, options or open answers. |
| Effect | IBM Plex Sans has no Arabic subset, so Arabic in reading text uses whatever fallback the platform supplies. "Arabic-capable fonts" is true only for display text in Readex Pro. If the team states NFR-05 as Done in these words, the claim is false. |
| Fix direction | Use IBM Plex Sans Arabic, or add an Arabic family as fallback, for the reading styles. |

### A-05
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Likely |
| Location | frontend/pubspec.yaml:37 |
| Quote | `google_fonts: ^8.2.1` |
| Trigger | The demo machine has no or poor internet when the app starts. |
| Effect | No font is bundled, so the app falls back to default fonts and the design does not appear as designed. |
| Fix direction | Bundle the font files as assets and turn off run-time fetching. |

### A-06
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:450 |
| Quote | `question.text,` |
| Trigger | A question or option is in Arabic. |
| Effect | Only open answers and the review answer use `directionOf`. Arabic question text keeps left-to-right direction, so it is left aligned and end punctuation can sit on the wrong side. |
| Fix direction | Apply `directionOf` to question, option and survey text. |

### A-07
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/app.dart:77 |
| Quote | `// Expired, not a respondent, or server down: fall back to login.` |
| Trigger | The app starts with a stored session while the server is down or answers 500. |
| Effect | The login screen appears with no message, although the session may still be valid. This is an unmet NFR-05 error state. |
| Fix direction | Show an error state with Try again for network and server failures. Keep login for a real session end. |

### A-08
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:370 |
| Quote | `value: (position * 100 / total).round(),` |
| Trigger | A published survey has zero questions. |
| Effect | There is no empty state, and 0/0 would throw when rounded. Normal use cannot reach this: survey_service.py:88 refuses to publish with no questions and questions are editable only in draft. Only a change through Django admin could. |
| Fix direction | Add an empty state on the start screen so NFR-05 holds literally. |

### A-09
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/profile/profile_screen.dart:523 |
| Quote | `'Some surveys are for certain groups. These details '` |
| Trigger | A respondent reads the Background section, or the hero text at profile_hero.dart:74 ("so more surveys can find you"). |
| Effect | The app promises something the backend does not do. Targeting uses only age, gender and region (targeting_service.py:131-143, survey_repository.py:30-48). Education, occupation, marital status and interests never affect matching (K-04 is still open). A committee member can check this. |
| Fix direction | Change the text, or implement the targeting in a later increment. |

### A-10
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | backend/tests/api/test_foundation.py:142 |
| Quote | `user = SimpleNamespace(` |
| Trigger | NFR-02 "refused on its next request" with a still-valid access token. |
| Effect | The refresh path has a real test, but nothing issues an access token, suspends the account and then calls an endpoint. The permission test uses a stand-in object. The behaviour rests on a library default that no project test pins. |
| Fix direction | Add an API test: authenticate, suspend through AdminService, call an endpoint, expect 401. |

### A-11
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | planning/API.md:189 |
| Quote | `Accounts suspended before the F-18 fix keep` |
| Trigger | A row has account_status SUSPENDED or DELETED and is_active true, from before the fix or from an edit in Django admin. |
| Effect | Respondent API calls answer 403, but refresh still issues tokens. The status rule is not in the services, so an existing web session of such a row continues. Migrations 0001 to 0006 contain no backfill. New suspensions are not affected. |
| Fix direction | Add a data migration that aligns is_active, and move the status check into the service layer. |

### A-12
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/login_screen.dart:100 |
| Quote | `ApiException.invalidCredentials => 'Email or password is incorrect.',` |
| Trigger | A suspended respondent logs in with the correct password. |
| Effect | They are told the password is wrong, although the server's message says the account is suspended or deleted (authentication_service.py:90). |
| Fix direction | Give suspended accounts their own error code and message after the password check passes. |

### A-13
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | planning/API.md:186 |
| Quote | `F-27: two parallel submits of the same survey can raise a database error, returned as 500` |
| Trigger | A reader compares the contract with the code. |
| Effect | Known Limits is stale and contradicts ticked issue 35. Also false: :184 one count query per survey (survey_repository.py:62 is one query), :187 emails case sensitive (authentication_service.py:96, `test_token_accepts_email_in_any_letter_case`), :188 passwords not checked for strength (serializers.py:93-99, `test_password_validation_rejects_weak_passwords`). |
| Fix direction | Remove or correct the four lines. |

### A-14
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/services/question_service.py:195 |
| Quote | `if not self.targeting_service.match_respondent_to_survey(respondent_user, survey_id):` |
| Trigger | `GET /surveys/{id}/` after the respondent has already submitted. |
| Effect | The form returns 200 with no duplicate check, unlike ensure_can_answer (response_service.py:68-70). The app is safe because the parallel draft call answers 409. No test covers it. May duplicate Part 2. |
| Fix direction | Reuse the same eligibility rule, including the duplicate check. |

### A-15
| Field | Content |
|---|---|
| Severity | Blocker |
| Confidence | Confirmed |
| Location | backend/static/js/site.js:136 |
| Quote | `colors: ["#12355b", "#0f766e", "#64748b"],` |
| Trigger | Reading ticked issue 61 criterion "No colour literal outside frontend/lib/theme and backend/static/css/tokens.css". |
| Effect | The ticked criterion is false. More literals are at site.js:147,155,162,309,310,422; analytics_dashboard.html:244,245,289,290; templates/base.html:31,208. PR 60 searched site.css only. It is cheap to fix, and it is a Blocker only under the rule that a false Done claim is one. |
| Fix direction | Read chart colours from the tokens, or narrow and reword the criterion. |

### A-16
| Field | Content |
|---|---|
| Severity | Blocker |
| Confidence | Confirmed |
| Location | backend/apps/responses/templates/responses/respondent_dashboard.html:74 |
| Quote | `Manage Demographic Profile` |
| Trigger | Reading ticked issue 61 criterion "labels are sentence case". |
| Effect | The ticked criterion is false on the web. Also :92, :110, eligible_surveys.html:43, provider_dashboard.html:20,24,98,107, survey_list.html:73,82, admin_dashboard.html:33,53. Blocker only under the false Done claim rule. |
| Fix direction | Change these labels to sentence case. |

### A-17
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | planning/STATUS.md:11 |
| Quote | `no manual check (D-125), first real use is the demo rehearsal` |
| Trigger | FR-06 goes to the demo on widget tests with a stubbed API only. |
| Effect | Draft and resume, including restart, have never been run against the real server, so a contract or runtime fault would first appear at rehearsal. STATUS.md is also stale: it names branch feat/fr06-drafts-app and an unmerged state. |
| Fix direction | Run the full flow by hand against the real server before the release PR, and refresh STATUS.md. |

### A-18
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Question |
| Location | frontend/android/app/src/debug/AndroidManifest.xml:6 |
| Quote | `<uses-permission android:name="android.permission.INTERNET"/>` |
| Trigger | The committee expects the "mobile app" on Android rather than in Chrome. |
| Effect | The debug manifest lacks the `usesCleartextTraffic` that API.md:17 says is needed. The main manifest has no INTERNET permission, so a release build cannot reach a server. ALLOWED_HOSTS is empty (checks.md:9), so `10.0.2.2` would get 400 DisallowedHost. CLAUDE.md says no emulator exists yet, so the app has never run on Android. Question: will the demo be on Android? If yes, this is a Blocker. |
| Fix direction | Decide the demo platform; if Android, fix the manifests and hosts and run it once. |

### A-19
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_start_screen.dart:390 |
| Quote | `title: 'Saved as you go',` |
| Trigger | The respondent types an answer and the app is killed or the browser tab is closed before the question changes. |
| Effect | That answer is lost. Saves happen on question change and on leaving (test `typing sends nothing until the question changes`), so the text promises slightly more than the code does. |
| Fix direction | Add a debounced save, or soften the wording. |

### A-20
| Field | Content |
|---|---|
| Severity | Blocker |
| Confidence | Confirmed |
| Location | planning/STATUS.md:12 |
| Quote | `FR-06 (#20) is then Done.` |
| Trigger | FR-01, FR-02 and FR-06 are counted as Done under KANBAN.md:34,37, which requires affected diagrams updated and the report section written. |
| Effect | `diagrams/` last changed 2026-10-29 and the report 2026-10-30, both before the FR-02 fields (c762367) and the draft table (b3d9928). The directory holds four PNGs and a README, with no PlantUML sources as CLAUDE.md describes. The Done claim fails the team's own definition. The report's content was not read. |
| Fix direction | Update the class and ER diagrams and report sections, or do not call these items Done yet. |

### A-21
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/register_screen.dart:250 |
| Quote | `controller: _password,` |
| Trigger | A respondent mistypes the password while registering. |
| Effect | The web form has confirm_password (apps/users/forms.py:48) and the app does not; only a show-password toggle helps. A partial replacement of web behaviour. |
| Fix direction | Add a confirm field, or record the toggle as the intended replacement. |

### A-22
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Question |
| Location | backend/apps/responses/forms.py:19 |
| Quote | `class DemographicProfileForm(BootstrapFormMixin, forms.Form):` |
| Trigger | A respondent uses the web profile or dashboard. |
| Effect | The web form has four fields and the dashboard shows only Complete or Incomplete, so education, occupation, marital status and the percent exist only in the app. Stored values are kept, not cleared. Question: is FR-02 meant for the app only? |
| Fix direction | Confirm the scope and record it. |

**Counts by severity: Blocker 4, Should 9, Later 9, Scope 0. Total 22.**


---

# TASK-21 audit, Part 2: API security and correctness

Target: develop @ b77dbb3. Finding range A-50 to A-99. Static reading only; nothing was executed.

**Read:** backend/apps/api/ (urls, views, serializers, permissions, exceptions); backend/services/ (response, authentication, profile, targeting, question, survey, admin, analysis); backend/repositories/ (response, draft, targeting, profile, user, question, survey); backend/apps/core/models/ (draft, response, answer, survey, question, user, profile, sentiment result); backend/core/exceptions.py; backend/config/settings.py and urls.py; backend/infrastructure/huggingface_client.py; backend/apps/analysis/views.py; backend/apps/users/views.py lines 1-130; backend/requirements.txt; backend/.env.example (search only); frontend/lib/core/api/api_client.dart; frontend/lib/features/answer/answer_repository.dart; planning/API.md; checks.md in the audit notes folder; backend/tests/api/test_throttling.py and part of test_auth.py.

**Not reached:**
- `.venv/**` is denied, so the source of Django 5.2.19, DRF 3.17.2 and simplejwt 5.5.1 was not read. Statements about library internals are marked "library". Where a repository test pins the behaviour, the test is cited. Findings that rest on library behaviour with no test are at most Likely.
- `backend/.env` is denied. DEBUG True and ALLOWED_HOSTS empty come from checks.md. USE_CELERY and REDIS_URL local values are unknown.
- `docs/**` is denied.

## 1. Endpoint table

Authentication "JWT" means the default JWTAuthentication (settings.py:122-124). Role "IsRespondent" means the default permission (settings.py:125, permissions.py:11-20). No endpoint takes a user id, so ownership is always "request.user".

| Endpoint | Authentication | Role check (where) | Ownership (where) | Throttle scope | Transaction | Error codes | Verdict |
|---|---|---|---|---|---|---|---|
| GET schema/ | none (SERVE_AUTHENTICATION []) | none | n/a | none | none | library | OK; public by setting (settings.py:166) |
| GET docs/ | none | none | n/a | none | none | library | OK; needs CDN (API.md:190) |
| POST auth/register/ | none | role forced to RESPONDENT in service (authentication_service.py:55) | n/a | auth_register 5/min | atomic, user + profile (authentication_service.py:62) | validation_error, parse_error, throttled; 500 possible | A-54 |
| POST auth/token/ | none | any role gets a token (documented API.md:32) | n/a | auth_token 10/min | one library row | validation_error, invalid_credentials, throttled | OK; A-59, A-58 |
| POST auth/token/refresh/ | none (library) | is_active only (test_auth.py:293) | token holder | auth_refresh 30/min | library, not atomic | validation_error, token_not_valid (library), throttled | OK |
| POST auth/logout/ | none | none | token holder | auth_logout 30/min | library | validation_error, invalid_token (built in the view), throttled | OK; A-58 |
| GET me/ | JWT | IsRespondent only; no service | request.user | none | none | not_authenticated, token_not_valid, authentication_failed, permission_denied | OK; A-57 |
| GET me/profile/ | JWT | IsRespondent + service (profile_service.py:34) | request.user | none | none | as above + not_found | OK |
| PUT me/profile/ | JWT | IsRespondent + service (profile_service.py:49) | request.user | none | one row | as above + validation_error | OK |
| GET profile/options/ | none | none | n/a | none | none | none | OK |
| GET surveys/eligible/ | JWT | IsRespondent + service (survey_service.py:158) | request.user | none | none | auth codes | OK |
| GET surveys/{id}/ | JWT | IsRespondent + service (question_service.py:185) | request.user; targeting in service | none | none | survey_not_found, not_editable, unauthorized_action | **A-50** |
| POST surveys/{id}/responses/ | JWT | IsRespondent + service (response_service.py:53) | request.user; targeting in service | none | atomic (response_service.py:86) | validation_error, survey_not_found, question_not_found, not_editable, unauthorized_action, duplicate_response | OK; A-51 |
| GET surveys/{id}/draft/ | JWT | IsRespondent + service | filtered by respondent id (draft_repository.py:9-12) | none | none | + draft_not_found | OK |
| PUT surveys/{id}/draft/ | JWT | IsRespondent + service | filtered by respondent id | none | atomic, one row (response_service.py:154) | + validation_error, question_not_found | OK; A-63, A-64 |
| DELETE surveys/{id}/draft/ | JWT | IsRespondent + service | filtered by respondent id | none | one statement | survey_not_found, not_editable, unauthorized_action, duplicate_response | OK |
| GET me/responses/ | JWT | IsRespondent + service (response_service.py:225) | filtered by respondent id (response_repository.py:30) | none | none | auth codes | OK |

## 2. Ownership and role

- **Another respondent's data:** not reachable. Draft, response and profile queries all use request.user's id. No endpoint accepts a user, draft or response id. Survey id only selects the survey.
- **Provider or admin acting as respondent:** refused on every respondent endpoint with 403 `permission_denied` by IsRespondent. Services repeat the role check, except GET me/ which has no service. They can still get a token (documented), and can call public endpoints.
- **Register cannot choose a role:** role is set in the service and the serializer has no role field.

## 3. Eligibility by path

Survey has no expiry field; "expired" does not exist in the model (survey.py:12-27). Closing is the only end state.

| Case | Detail GET | Submit POST | Draft GET | Draft PUT | Draft DELETE |
|---|---|---|---|---|---|
| Survey missing | 404 survey_not_found | 404 | 404 | 404 | 404 |
| Draft status or closed | 409 not_editable | 409 | 409 | 409 | 409 |
| Not targeted, no criteria, incomplete profile | 403 unauthorized_action | 403 | 403 | 403 | 403 |
| Already answered | **200, full form (A-50)** | 409 duplicate_response | 409 | 409 | 409 |
| Implementation | question_service.py:183-198 | response_service.py:51-72 | same | same | same |

The body is validated by the serializer before the service, so a malformed PUT or POST to a closed or missing survey gets 400 before these checks (see A-55). List and detail targeting rules agree: survey_repository.py:30-48 and targeting_service.py:131-143 express the same gender, age and region rules.

## 4. Suspended and inactive accounts

| Stage | Where checked | Result |
|---|---|---|
| Login | authentication_service.py:89, account_status only | 401 invalid_credentials for SUSPENDED or DELETED. is_active is not checked (A-59). |
| Valid access token, each request | JWTAuthentication loads the user and checks is_active per request (library); then permissions.py:17-19 checks is_active and account_status per request | Normal suspension sets both fields (user.py:76-85), so the next request is refused with 401 (library). Old rows with SUSPENDED and is_active True get 403 (test_foundation.py:139-144). |
| Refresh | simplejwt serializer, is_active rule (library; pinned by test_auth.py:293) | 401 after normal suspension. Old rows with is_active True still refresh (documented API.md:189), but every endpoint then answers 403. |

NFR-02 "refused on its next request" holds for accounts suspended through AdminService. The check is per request, not only at login.

## 5. Throttling

| Endpoint | Scope (views.py) | Rate (settings.py:127-132) |
|---|---|---|
| auth/token/ | auth_token (line 76) | 10/min |
| auth/token/refresh/ | auth_refresh (line 125) | 30/min |
| auth/register/ | auth_register (line 49) | 5/min |
| auth/logout/ | auth_logout (line 98) | 30/min |

- **Key:** client address with NUM_PROXIES 0 (settings.py:133). test_throttling.py:57-65 proves X-Forwarded-For does not reset the limit.
- **429 shape:** `{"error":{"code":"throttled","message":...}}` with Retry-After, pinned by test_throttling.py:41-43.
- **Cache:** without REDIS_URL Django's per-process default cache applies (settings.py:140-147). It works with one runserver process. It multiplies the limit with several workers (A-61). `.env.example:19` has REDIS_URL commented out; the local value was not read.
- **Gap:** the web login has no throttle (A-60).

## 6. Token handling

ROTATE_REFRESH_TOKENS and BLACKLIST_AFTER_ROTATION are on (settings.py:157-158), and the blacklist app is installed (settings.py:37). Logout blacklists the refresh token (views.py:114-115). A used, invalid or wrong-type token raises TokenError and returns 400 `invalid_token` (views.py:116-120). The access token stays valid up to 30 minutes after logout (documented API.md:27). The app has a single-flight refresh (api_client.dart:69-74).

## 7. Server-side limits

Both paths use the same validators in response_service.py. No gap found.

| Rule | Submit | Draft PUT | Evidence |
|---|---|---|---|
| Open text at most 2000 | yes | yes | serializers.py:162-163; response_service.py:321 |
| Rating 1 to 5, integer | yes | yes | response_service.py:338-343 |
| Option belongs to question | yes | yes | response_service.py:359-365 |
| Question belongs to survey | yes, 404 | yes, 404 | response_service.py:97-100, 265-266; 142-144 |
| Required questions | yes | not required by design | response_service.py:249-259; 145 |
| Duplicate question in payload | yes, 400 | yes, 400 | response_service.py:242-243; serializer coerces "1" and 1 to the same integer |
| Wrong field for question type | yes | yes | response_service.py:312-315, 331-334, 347-350 |
| Multi-choice arrays | not supported; single integer, array gives 400 | same | serializers.py:170 |
| Stored draft size | n/a | bounded: each entry must be a distinct question of the survey, each text at most 2000 | response_service.py:141-147 |
| Request body size | no explicit limit | no explicit limit | A-62 |

## 8. Error shape and malformed input

Every DRF view uses `api_exception_handler` (settings.py:137). Exception: logout's 400 is hand-built with the same shape (views.py:117).

| Input | Result |
|---|---|
| Broken JSON, wrong JSON type for body, list instead of object | 400 parse_error or validation_error (library behaviour plus handler exceptions.py:46-55) |
| answers null, missing, not a list, list of non-objects | 400 validation_error |
| question_id null, missing, text, boolean | 400 validation_error |
| rating_value or selected_option_id wrong type | 400 validation_error |
| NUL character in text | 400 (library CharField validator) |
| Very large survey id in URL | expected 404 (library integer overflow handling; no test) |
| Non-numeric id or unknown URL | Django HTML 404, not the shared shape (A-65) |
| Email of 255 to 320 characters on register | **500 internal_error (A-54)** |
| Any unhandled exception | 500 internal_error JSON (exceptions.py:35-40) |

## 9. Transactions and races

| Scenario | Trace | Result |
|---|---|---|
| Two parallel submits | Both pass the pre-check. Second insert hits unique_response_per_survey_respondent (response.py:27-30), caught at response_service.py:115-118 | 409. NFR-03 holds. Test: test_responses.py:243. API.md:186 is stale (A-55). |
| Submit during draft save | Save can write after the submit deleted the draft | Orphan row, no user effect (A-63) |
| Two first saves of a draft | Second insert hits the constraint; falls back to update (response_service.py:156-163) | Correct; one rare 500 path (A-64) |
| Draft deletion after submit | ensure_can_answer raises duplicate | 409 duplicate_response, documented |
| Multi-row writes | Register atomic; submit atomic; add options atomic. Sentiment atomic (A-52) | Rule met on API paths |

Known issues, real state at b77dbb3:

| ID | State | Evidence |
|---|---|---|
| K-01 | Fixed | response_service.py:85-114 |
| K-02 | Partly. Runs after commit in an on_commit callback with robust=True, but still inside the HTTP request unless USE_CELERY is on | response_service.py:111-114, 180-192 (A-51) |
| K-03 | Fixed in substance. Profile region and criteria region are Governorate codes, compared by equality | targeting_service.py:118, 141 |
| K-04 | Still open. Matching has no interests rule | targeting_service.py:129-143 |
| K-12 | Fixed. Analytics ownership is in the service; the view is thin | analysis_service.py:108-118; analysis/views.py:16-17 |

**Hugging Face failure on submit:** 402 becomes HTTPError and a timeout becomes RequestException. Both become ExternalAnalysisServiceError (huggingface_client.py:57-64), caught per answer, and the result is marked FAILED (analysis_service.py:61-62). Submit still returns 201. Anything unexpected is swallowed by robust=True. The cost is delay (A-51) and a silent lack of results (A-53).

## 10. N+1 in list endpoints

No finding. Eligible uses one annotated query with select_related (survey_repository.py:50-65); API.md:184 is stale. Answered uses select_related (response_repository.py:29-33). Detail prefetches options (question_repository.py:24-26). Option lookups in submit run per answer but are bounded by survey size.

## 11. Settings for the demo

| Setting | State | Matters for local demo |
|---|---|---|
| DEBUG | Env, default False (settings.py:13); True locally (W018) | No. Needed: CORS for Chrome is DEBUG-only. |
| SECRET_KEY | Env; dev fallback literal at settings.py:19 only if DEBUG and unset; required otherwise (settings.py:15-17) | No. W009 not raised, so the local key is not weak. |
| ALLOWED_HOSTS | Env, empty locally (W020) | Not for localhost or 127.0.0.1. Yes for an emulator or phone (A-66). |
| CORS | localhost and 127.0.0.1 regexes in DEBUG only (settings.py:173-177), /api/ only, no credentials | Fine for Chrome |
| JWT lifetimes | 30 minutes, 7 days (settings.py:118-119) | Fine |
| W004, W008, W012, W016 (HSTS, SSL redirect, secure cookies) | Set only when DEBUG is False (settings.py:186-195) | No. Local demo is plain http. Matter only for a real deployment. |
| W018 DEBUG, W020 ALLOWED_HOSTS | Local .env values | Must change for deployment only |

## 12. Findings

### A-50
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | backend/services/question_service.py:183 |
| Quote | `def _ensure_respondent_can_answer(self, respondent_user, survey_id):` |
| Trigger | A respondent who already submitted survey 5 calls GET /api/v1/surveys/5/ (for example from a stale list, or after answering on the web). |
| Effect | The API returns 200 with the full form instead of 409 duplicate_response. Submit and all three draft calls answer 409 for the same survey, so eligibility differs by path. The rule is implemented twice and the copy lacks the duplicate check. The web form uses the same method (apps/responses/views.py:100). |
| Fix direction | Make the detail path use the single eligibility rule in ResponseService.ensure_can_answer, and add a service test. |

### A-51
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | backend/services/response_service.py:192 |
| Quote | `self.analysis_service.analyze_open_text_answers(response_id)` |
| Trigger | USE_CELERY is off (settings.py:215 default; `.env.example:18` commented; local value not read) and Hugging Face stalls. Each answer can wait 15 s for read and 15 s for connect (huggingface_client.py:26). Four stalled reads, or two answers using both limits, reach the app's 60 s limit (answer_repository.dart:10). |
| Effect | The response is already committed and the draft deleted, but the app waits, then shows a network error. A retry gets 409. K-02 is reduced, not closed. A shorter stall still shows a long spinner in the demo. |
| Fix direction | Do not call Hugging Face inside the request by default (run it in the background or cap total analysis time). |

### A-52
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/services/analysis_service.py:41 |
| Quote | `@transaction.atomic` |
| Trigger | Any submit with open-text answers: the decorator wraps the loop that makes the Hugging Face HTTP call at line 55. |
| Effect | A database transaction stays open during every external call, up to tens of seconds per submit. No visible effect at demo load. It wastes connections under real load. |
| Fix direction | Make the external call outside the transaction and write each result in a short one. |

### A-53
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | backend/services/analysis_service.py:62 |
| Quote | `result.mark_failed()` |
| Trigger | Hugging Face answers 402 (credits used), times out, or the token is missing. |
| Effect | Submit still succeeds, but the sentiment row stays FAILED. Nothing re-runs it: the only callers are response_service.py:192 and apps/core/tasks.py:21. get_survey_results returns no failed or pending count (lines 96-106), so the provider dashboard shows 0 positive, neutral and negative with no explanation. May duplicate Part 4. |
| Fix direction | Expose failed and pending counts in the analytics and provide a way to re-run failed analyses. |

### A-54
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Likely (validator length limit is library behaviour, source not reached, no test) |
| Location | backend/apps/api/serializers.py:90 |
| Quote | `email = serializers.EmailField()` |
| Trigger | POST auth/register/ with a syntactically valid email of 255 to 320 characters. The column is 254 (apps/core/migrations/0001_initial.py:32). |
| Effect | PostgreSQL raises DataError, which `except IntegrityError` at authentication_service.py:75 does not catch, so the client gets 500 internal_error instead of 400. |
| Fix direction | Limit the serializer email to 254 characters, the column size. |

### A-55
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | planning/API.md:186 |
| Quote | `F-27: two parallel submits of the same survey can raise a database error` |
| Trigger | A team member relies on the API.md "Known limits" list when answering the committee. |
| Effect | The list is stale. Line 186: parallel submits return 409 (response_service.py:115-118), so NFR-03 looks unmet when it is met. Line 187: emails are normalised to lower case and matched case-insensitively (authentication_service.py:96, user_repository.py:19). Line 188: password strength is checked (serializers.py:93-99, settings.py:90-103). Line 184: eligible counts are one annotated query (survey_repository.py:62). Line 126 says the checks come first, but the serializer's 400 for a malformed body comes before them (views.py:339-343). |
| Fix direction | Update the Known limits list and the check-order sentence to match the code. |

### A-56
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | CLAUDE.md:70 |
| Quote | `K-01 ResponseService.submit_response is not atomic.` |
| Trigger | Anyone reading the Known issues list. |
| Effect | K-01 (line 70), K-03 (line 72) and K-12 (line 78) describe defects that are fixed; K-02 (line 71) is outdated in detail. See the state table in section 9. |
| Fix direction | Mark K-01, K-03 and K-12 fixed and reword K-02. |

### A-57
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/apps/api/permissions.py:19 |
| Quote | `and getattr(user, "account_status", AccountStatus.ACTIVE) == AccountStatus.ACTIVE` |
| Trigger | Reading the claim that role and status rules live only in the business layer (NFR-02 and the architecture rule). |
| Effect | The per-request account status rule exists only in the API permission class, not in a service. Roles are repeated in services, except GET me/, which relies on the permission alone. Behaviour is correct; the claim is only partly true. |
| Fix direction | Move the status rule to a service method that the permission calls, or state the exception in the report. |

### A-58
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/apps/api/views.py:115 |
| Quote | `token.blacklist()` |
| Trigger | Every logout; also token creation at line 93. |
| Effect | Token creation and revocation write to the database from the view through the library, skipping the service layer. Logout's error is hand-built at line 117 instead of going through the shared handler; the shape is the same. No user-visible effect. |
| Fix direction | Move token issue and revocation into AuthenticationService and raise a mapped exception. |

### A-59
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Likely (the rejection after login is library behaviour) |
| Location | backend/services/authentication_service.py:89 |
| Quote | `if user.account_status in {AccountStatus.SUSPENDED, AccountStatus.DELETED}:` |
| Trigger | is_active is cleared in Django admin while account_status stays ACTIVE. |
| Effect | Login returns tokens, then the next call and the refresh are refused, so the app logs the user out straight after a successful login. AdminService always sets both fields, so this needs Django admin. |
| Fix direction | Refuse login when is_active is false as well. |

### A-60
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed (Question for the team: does NFR-02 cover the web login?) |
| Location | backend/apps/users/views.py:93 |
| Quote | `def login_view(request):` |
| Trigger | Repeated POSTs to the web login page against one account. No decorator on the view and no throttling middleware (settings.py:47-57). |
| Effect | Password guessing is unlimited through the web form, which calls the same authenticate_user as the API. "Login is throttled" is true only for the API. The web register views are also unthrottled. |
| Fix direction | Rate-limit the web login, or state in the report that throttling covers the mobile API only. |

### A-61
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Likely (local REDIS_URL not read) |
| Location | backend/config/settings.py:141 |
| Quote | `if REDIS_URL:` |
| Trigger | Running several workers (gunicorn is in requirements.txt:14) without REDIS_URL. No Redis service or gunicorn command was found in docker-compose.yml. |
| Effect | Each worker counts separately, so the real limit is the rate times the worker count. The demo on one runserver process is not affected. Already documented at API.md:171. |
| Fix direction | Require a shared cache when deploying with more than one worker. |

### A-62
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Likely (whether DATA_UPLOAD_MAX_MEMORY_SIZE applies to the JSON parser is library behaviour) |
| Location | backend/apps/api/serializers.py:182 |
| Quote | `answers = AnswerSerializer(many=True)` |
| Trigger | A very large JSON body with a huge answers list. |
| Effect | The whole list is parsed and validated before the service rejects it, which costs memory and CPU. Stored size stays bounded. |
| Fix direction | Set a maximum list length and an explicit request size limit. |

### A-63
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/services/response_service.py:148 |
| Quote | `draft = self.draft_repository.find(survey_id, user.user_id)` |
| Trigger | A draft PUT passes ensure_can_answer just before a submit commits, then writes after it. |
| Effect | A draft row remains after the submit, so "a successful submit deletes the draft" (API.md:94) is not strictly true. The row is unreachable because all draft calls answer 409. No user effect. |
| Fix direction | Re-check for a response inside the save, or clean up such rows. |

### A-64
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/services/response_service.py:162 |
| Quote | `draft.answers = stored_answers` |
| Trigger | Two parallel first saves, and the winning draft is deleted or submitted before the loser re-reads it at line 161. |
| Effect | The lookup returns None, AttributeError follows, and the client gets 500 internal_error. Very rare. |
| Fix direction | Handle a missing draft in the fallback path. |

### A-65
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | backend/apps/api/urls.py:17 |
| Quote | `path("surveys/<int:survey_id>/", views.SurveyDetailView.as_view(), name="survey-detail"),` |
| Trigger | GET /api/v1/surveys/abc/ or any unknown API URL. |
| Effect | Django returns an HTML 404, so "every error has one shape" (API.md:141) has an exception, documented at API.md:182. The app only sends integer ids. |
| Fix direction | Add a JSON 404 for paths under /api/. |

### A-66
| Field | Content |
|---|---|
| Severity | Should (Blocker if the demo runs on Android) |
| Confidence | Question: will the demo use an emulator or phone? |
| Location | backend/config/settings.py:20 |
| Quote | `ALLOWED_HOSTS = [` |
| Trigger | The app connects through 10.0.2.2 or the laptop's LAN address while ALLOWED_HOSTS is empty (W020 in checks.md). |
| Effect | Every request gets 400 DisallowedHost, as API.md:16 warns. Chrome on localhost is fine. FR-01 is a mobile app and CLAUDE.md records no Android emulator yet. |
| Fix direction | Decide the demo device now and, if Android, set ALLOWED_HOSTS in the local .env and rehearse it. |

## Count

Blocker 0, Should 7, Later 10, Scope 0. Total 17.


---

# TASK-21 audit, Part 3: API contract

Target: develop @ b77dbb3. Finding IDs A-100 to A-115.

**Read:** planning/API.md (whole). backend/apps/api/ (urls, views, serializers, exceptions, permissions). backend/services/ (response, authentication, profile, question, survey). backend/core/ (exceptions, enums). backend/apps/core/models/ (user, respondent_profile, response, response_draft, survey, question, question_option). Migrations 0004 and 0005. backend/repositories/ (survey and user, the relevant functions). backend/config/settings.py and urls.py (API parts). Every file in frontend/lib/core/api/, every repository and model in frontend/lib/features/, and the screens and widgets that consume their errors. Android manifests (search). Flutter SDK text_formatter.dart (search).

**Not reached:** docs/**, backend/.env and .venv/** are denied by the corrected brief. checks.md was not needed for this part. No test was run and no server was called, so every result below comes from reading code.

**Access disclosure:** before the coordinator's correction arrived, this auditor read docs/audit/BRIEF.md, and read or searched library source under .venv/ (rest_framework_simplejwt exceptions.py, authentication.py, serializers.py, views.py; rest_framework views.py, fields.py). The correction denies those paths, and they were not opened again. Three findings rest partly on that library source and cannot be re-checked under the corrected brief: A-101, A-108 (the interests part only) and A-113. Re-verify them against the library or with a request before acting.

Legend for the tables: `views` = backend/apps/api/views.py, `ser` = backend/apps/api/serializers.py, `exc` = backend/apps/api/exceptions.py, `API` = planning/API.md. Dart files are under frontend/lib/.

## 1. Endpoint and status table

"401 set" below means `not_authenticated` (no token), `token_not_valid` (bad or expired token), `authentication_failed` (inactive or missing user). Server source for all of them: settings.py:122-125 and exc:53-55. App handling for all of them: api_client.dart:60-64 refreshes once and retries; a failed refresh raises SessionExpiredException and returns to login.

"403 role" means `permission_denied` from permissions.py:11-20 (settings.py:125).

| Endpoint | Status and code | API.md | Server | App | Result |
|---|---|---|---|---|---|
| POST auth/register/ | 201 {id,email,name,role} | API:37 | views:72, ser:11-17 | auth_repository.dart:49 (body ignored) | OK |
| | 400 validation_error with fields | API:37,67 | views:60, ser:34-53,89-99 | register_screen.dart:140-148, shown under each input | OK; password rule see A-103 |
| | 400 validation_error, no fields (duplicate email, password like user data) | API:37 | authentication_service.py:50,58,103,108 | register_screen.dart:147, form line | OK |
| | 429 throttled | API:37,166 | views:49, settings.py:130 | register_screen.dart:147, raw server text | OK |
| POST auth/token/ | 200 {access,refresh} | API:38 | views:94 | auth_repository.dart:24-35 | OK |
| | 400 validation_error | API:38 | views:87, ser:105-106 | login_screen.dart:98-103 | OK |
| | 401 invalid_credentials | API:22,38 | authentication_service.py:87,90 | login_screen.dart:100 | A-111 |
| | 429 throttled | API:38,164 | views:76, settings.py:128 | login_screen.dart:102, raw server text | OK |
| POST auth/token/refresh/ | 200 {access,refresh} | API:24,39 | views:130, settings.py:157-158 | api_client.dart:83-98, stores both | OK |
| | 400 validation_error | API:39 | views:130 | api_client.dart:87 session expired | OK |
| | 401 token_not_valid | API:39, code missing at API:148 | views:130 | api_client.dart:87 session expired | A-101 |
| | 401 authentication_failed (inactive account) | API:39 | views:130; test at tests/api/test_auth.py:293 | api_client.dart:87 session expired | OK |
| | 429 throttled | API:39,165 | views:125, settings.py:129 | api_client.dart:91, ApiException, tokens kept | OK |
| | 500 internal_error (user row hard-deleted) | not listed | views:130, exc:35-40 | api_client.dart:91, tokens kept | A-113 |
| POST auth/logout/ | 204 | API:26,40 | views:121 | auth_repository.dart:87-97 | OK |
| | 400 validation_error | API:40 | views:112 | auth_repository.dart:93, ignored | OK |
| | 400 invalid_token | API:147 | views:116-120 | auth_repository.dart:93, ignored | OK |
| | 429 throttled | API:40,167 | views:98, settings.py:131 | auth_repository.dart:93, ignored | OK |
| GET me/ | 200 {id,email,name,role} | API:41 | views:141, ser:11-17 | auth_repository.dart:67-71, auth_models.dart:10-17 | OK |
| | 401 set | API:41 | as above | as above | A-101 for the code list |
| | 403 role | API:41 | as above | auth_repository.dart:73-75, clears tokens | OK |
| GET me/profile/ | 200 profile | API:42 | views:155, ser:56-66 | profile_repository.dart:18-27, profile_models.dart:59-68 | OK |
| | 401 set, 403 role | API:42 | as above | profile_screen.dart:120-127 | OK |
| | 404 not_found | API:42,150 | views:154 | profile_repository.dart:23, returns null | OK |
| PUT me/profile/ | 200 profile | API:43 | views:180 | profile_repository.dart:30-33 | OK |
| | 400 validation_error with fields | API:43,67 | views:166, ser:34-66 | profile_screen.dart:237-250 | OK from the app; shape see A-108 |
| | 401 set, 403 role | API:43 | as above | profile_screen.dart:235-258 | OK |
| GET profile/options/ | 200 five lists | API:44,70-78 | views:193, ser:69-83, profile_service.py:66-74 | profile_repository.dart:12-15, profile_models.dart:5-35 | OK; codes and order match core/enums.py |
| GET surveys/eligible/ | 200 plain array | API:45 | views:205, ser:116-122 | surveys_repository.dart:11-24, surveys_models.dart:10-17 | OK |
| | 401 set, 403 role | API:45 | as above | eligible_surveys_screen.dart:51,232-239 | OK |
| GET surveys/{id}/ | 200 detail | API:46,82 | views:222, ser:125-155 | answer_repository.dart:14-17, answer_models.dart:26-76 | OK |
| | 401 set, 403 role | API:46 | as above | survey_start_screen.dart:61-64 | OK |
| | 403 unauthorized_action | API:149 | question_service.py:196 | survey_parts.dart:62 | OK |
| | 404 survey_not_found | API:46 | question_service.py:190 | survey_parts.dart:67 | OK |
| | 409 not_editable | API:46,152 | question_service.py:193 | survey_parts.dart:54 | OK |
| | 200 for an already answered survey | not stated | question_service.py:183-198 has no duplicate check | blocked by the parallel draft call, survey_start_screen.dart:49-52 | OK |
| | HTML 404 (non-numeric id) | API:182 | urls.py:17 | app builds integer ids only | OK |
| POST surveys/{id}/responses/ | 201 {id,survey_id,submitted_at} | API:47 | views:276-279, ser:200-205 | answer_repository.dart:20-27, answer_models.dart:169-174 | OK |
| | 400 validation_error, nested fields | API:47,143 | views:272, ser:158-182 | survey_answer_screen.dart:216-223,242-247 | A-108, A-109 |
| | 400 validation_error, no fields | API:47 | response_service.py:230-243,249-365 | survey_answer_screen.dart:221 | OK |
| | 401 set, 403 role | API:47 | as above | survey_answer_screen.dart:189-192 | OK |
| | 403 unauthorized_action | API:47,149 | response_service.py:66 | survey_parts.dart:62 | OK |
| | 404 survey_not_found | API:47 | response_service.py:57 | survey_parts.dart:67 | OK |
| | 404 question_not_found | API:150 | response_service.py:100,266 | survey_answer_screen.dart:231-238, snackbar | OK; app cannot trigger it |
| | 409 not_editable | API:47,152 | response_service.py:60 | survey_parts.dart:54 | OK |
| | 409 duplicate_response | API:47,152 | response_service.py:70,118 | survey_answer_screen.dart:211, survey_parts.dart:49 | OK; parallel case see A-102 |
| GET surveys/{id}/draft/ | 200 draft | API:48,115 | views:322, ser:191-197 | answer_repository.dart:30-39, answer_models.dart:117-137 | OK |
| | 404 draft_not_found | API:135 | response_service.py:129 | answer_repository.dart:35, returns null | OK |
| | 401 set, 403 role, 403 unauthorized_action, 404 survey_not_found, 409 not_editable, 409 duplicate_response | API:48,130-134 | response_service.py:53-70 | survey_start_screen.dart:61-75, survey_parts.dart:49-67 | OK |
| PUT surveys/{id}/draft/ | 200 draft | API:49,102 | views:344 | answer_repository.dart:42-44, body ignored | OK |
| | 400 validation_error | API:136 | views:340, response_service.py:140-145 | survey_answer_screen.dart:116-124 | A-107, A-110 |
| | 404 question_not_found | API:137 | response_service.py:144 | survey_answer_screen.dart:124 | A-110; app cannot trigger it |
| | 401 set, 403 role, 403 unauthorized_action, 404 survey_not_found, 409 not_editable, 409 duplicate_response | API:49,130-134 | response_service.py:134 | survey_answer_screen.dart:113-123 | OK |
| DELETE surveys/{id}/draft/ | 204, also with no draft | API:50,103 | views:359, response_service.py:165-168 | answer_repository.dart:46-48, api_client.dart:129 | OK |
| | 401 set, 403 role, 403 unauthorized_action, 404 survey_not_found, 409 not_editable, 409 duplicate_response | API:50,130-134 | response_service.py:167 | survey_start_screen.dart:134-152 | OK |
| GET me/responses/ | 200 plain array | API:51 | views:371, ser:208-214, response_service.py:201-216 | not used | A-100 |
| | 401 set, 403 role | API:51 | as above | not used | A-100 |
| GET schema/, GET docs/ | 200 | API:10-11 | urls.py:7-8, settings.py:166-167 | not used | A-114 for content |
| Any | 405 method_not_allowed | API:151 | exc:53-55 | app uses only documented methods | OK |
| Any body or negotiation | 415 unsupported_media_type, 406 not_acceptable | not listed | settings.py:134-135, exc:53-55 | app always sends JSON (api_client.dart:109,114) | A-101 |
| Any | 500 internal_error | API:154 | exc:35-40 | shown as raw server text | OK |

**Endpoint coverage.** Every endpoint in API.md exists on the server. Every server endpoint under /api/v1/ is in API.md (schema and docs are in the Base URL table). The app calls every endpoint except GET me/responses/ (A-100) and schema/docs.

## 2. Response parsers, field by field

No server field can be null for any field the Dart parser casts to non-nullable. The database columns are all NOT NULL, as listed below. This means no input makes a parser crash on null at b77dbb3.

| Dart parser | Field and cast | Server field | Column | Can it be null? |
|---|---|---|---|---|
| AppUser auth_models.dart:12-15 | id int; email, name, role String | ser:14-17 | user.py:42,44-46 | No |
| ChoiceOption profile_models.dart:6-7 | code, label String | ser:72-73 | enum values | No |
| Profile profile_models.dart:60 | age int | ser:34 | respondent_profile.py:37 NOT NULL | No |
| Profile :61-62 | gender, region String | ser:35-36 | :38,:41 NOT NULL; region may be "" for rows migration 0004 could not map | No; "" is handled at profile_screen.dart:147 |
| Profile :63 | interests List of String | ser:40 | :42 ArrayField default list | No; may be [] |
| Profile :64-66 | education, occupation, marital_status String | ser:59-65 | :47-55 default "" | No |
| Profile :67 | completion_percent int | ser:66 | method at :109 returns int | No |
| EligibleSurvey surveys_models.dart:12-15 | id int; title String; description String?; question_count int | ser:119-122 | survey.py:12,18,19; annotated at survey_repository.py:62 | No |
| SurveyDetail answer_models.dart:69-73 | order_index, id int; title String; description String? | ser:139,153-154 | question.py:18, survey.py:12,18,19 | No |
| SurveyQuestion :28-43 | id int; text String; type enum; is_required bool; options; rating_values | ser:135-141 | question.py:9,15-17 | No |
| QuestionOption :8 | id int; text String | ser:128-129 | question_option.py:7,13 | No |
| SurveyDraft :120-126 | answers; question_id int; started_at, updated_at parsed | ser:194-197, stored shape response_service.py:170-176 | response_draft.py:19-21 | No |
| SubmitResult :171-172 | id int; submitted_at parsed | ser:203,205 | response.py:10,22 | No |

Unexpected shapes are caught: TypeError at auth_repository.dart:78, profile_repository.dart:41, surveys_repository.dart:21; TypeError and FormatException at answer_repository.dart:77-80.

**Types.** All ids are integers on both sides. The API has no decimal field. Dates are ISO 8601 in UTC with `Z` (settings.py:106,108) and Dart DateTime.parse accepts them with microseconds. Question types match (core/enums.py:31-33, answer_models.dart:31-33). The hard-coded gender codes match ser:8. The app's hard-coded list codes (choice_select_field.dart:8, interest_icons.dart:5-16) match core/enums.py. Sentiment is not exposed by this API.

## 3. Request bodies and URLs

| Call | App sends | Server expects | Result |
|---|---|---|---|
| register | name, email, password, age int, gender, region, interests list (auth_repository.dart:51-59) | ser:34-47,89-91 | OK |
| login | email, password (:26) | ser:105-106 | OK |
| refresh | refresh (api_client.dart:83-85) | library serializer | OK |
| logout | refresh, no Authorization (auth_repository.dart:87-91) | ser:176, views:44 | OK |
| profile PUT | seven fields (profile_models.dart:82-90) | ser:34-47,59-65 | OK |
| submit, draft PUT | answers[question_id, selected_option_id, rating_value, answer_value] (answer_repository.dart:50-65) | ser:161-170,182,188 | OK; length rule see A-109 |

All paths the app builds end with a slash and match urls.py. Methods match. **Pagination:** no list is paginated (settings.py:121-138 has no pagination class, views:205,371 return plain arrays), and API:3,181 and surveys_repository.dart:13 agree.

## 4. Error codes against the app's mapping

| Code | Status | App recognises it at | User sees |
|---|---|---|---|
| validation_error | 400 | survey_answer_screen.dart:216; field errors in forms | Field text, or the server message |
| parse_error | 400 | no mapping | Server message; app always sends valid JSON |
| invalid_token | 400 | auth_repository.dart:93 | Nothing; logout continues |
| not_authenticated, token_not_valid, authentication_failed | 401 | by status, api_client.dart:60 | Silent refresh, else "Your session ended. Please log in again." |
| invalid_credentials | 401 | login_screen.dart:100 | "Email or password is incorrect." (A-111) |
| permission_denied | 403 | by status at auth_repository.dart:73 only | Login: "This app is for respondents..."; elsewhere the server message with Try again |
| unauthorized_action | 403 | survey_parts.dart:62 | "This survey no longer matches your profile" |
| survey_not_found | 404 | survey_parts.dart:67 | "This survey is not available" |
| draft_not_found | 404 | answer_repository.dart:35 | Nothing; starts with no draft |
| question_not_found | 404 | no mapping | Submit: "Not sent. ..." snackbar. Draft: A-110. App cannot trigger it |
| not_found | 404 | by status, profile_repository.dart:23 | Empty profile form |
| duplicate_response | 409 | survey_answer_screen.dart:211, survey_parts.dart:49 | "You already answered this survey" |
| not_editable | 409 | survey_parts.dart:54 | "This survey is closed" |
| throttled | 429 | no mapping | Raw server text with the wait in seconds; only auth endpoints emit it |
| internal_error | 500 | no mapping | "Unexpected server error." |
| HTML body | any | api_client.dart:135-136 | "The server sent an unexpected response." |

`account_not_found`, `response_not_found`, `targeting_criteria_not_found` and `external_service_error` are mapped at exc:15,16,18,24, but no API path raises them. Sentiment errors stay inside the robust on_commit at response_service.py:111-114.

## 5. Findings

| ID | Severity | Confidence | Location | Quote | Trigger | Effect | Fix direction |
|---|---|---|---|---|---|---|---|
| A-100 | Blocker (if FR-01 is claimed Done) | Confirmed | planning/API.md:51; server backend/apps/api/views.py:370; the only list call is frontend/lib/features/surveys/surveys_repository.dart:12 | `` GET \| `/me/responses/` `` | A respondent looks for surveys already answered | No file in frontend/lib calls me/responses/ and no screen exists. UC-06 is missing from the app, so "covering everything the respondent web pages offer" is false. Confirms D-127. May duplicate Part 1 or Part 4. | Add the answered-surveys screen, or remove UC-06 from the claim. |
| A-101 | Should | Confirmed (library evidence, see header) | planning/API.md:148 | `` `not_authenticated`, `authentication_failed`, `invalid_credentials` `` | An expired or invalid access or refresh token; also a non-JSON Content-Type or an unsupported Accept header | The most common 401 code, `token_not_valid`, is missing from the documented list, as are 415 `unsupported_media_type` and 406 `not_acceptable`. The app works by status, so users see nothing; the written contract is wrong. | Add the three codes to the table. |
| A-102 | Should | Confirmed | planning/API.md:186; code backend/services/response_service.py:115-118 | `F-27: two parallel submits of the same survey can raise a database error` | A reader checks NFR-03 in API.md | The document says a parallel duplicate gives 500. The code catches the named constraint (migration 0001:177) and raises 409. The document understates a requirement the code meets. May duplicate Part 2. | Delete the F-27 line. |
| A-103 | Should | Confirmed | planning/API.md:188; code backend/apps/api/serializers.py:96, backend/config/settings.py:90 | `Passwords are not checked for strength (same as the web form).` | Register with a short or common password | The server returns 400 `fields.password`, the opposite of the document. The app shows it under the input and gives no rule in advance. | Correct the line. |
| A-104 | Later | Confirmed | planning/API.md:187; code backend/repositories/user_repository.py:19, backend/services/authentication_service.py:96 | `F-26: emails are case sensitive.` | Log in with different letter case | Login works, because the service lowercases and the lookup uses iexact. The known limit is out of date. | Delete the line. |
| A-105 | Later | Confirmed | planning/API.md:184; code backend/repositories/survey_repository.py:62 | `The eligible list runs one count query per survey (small lists).` | Reading the document | The count is one annotated query. The known limit is out of date. | Delete the line. |
| A-106 | Later | Confirmed | planning/API.md:32; code backend/apps/api/views.py:97,124 | `` on every endpoint except register, token and `GET /profile/options/` `` | A provider token holder calls refresh or logout | Both succeed, because they take no authentication and no role check. The exception list leaves them out. | Add refresh and logout to the list. |
| A-107 | Later | Confirmed | planning/API.md:126; code backend/apps/api/views.py:340 | `` are checked in this order, so after a submit every call answers 409 `duplicate_response` `` | PUT draft with a malformed body on a closed or already submitted survey | The server answers 400, because the serializer runs before the service. The document promises the 409 first and "every call". | State that body validation comes first. |
| A-108 | Later | Confirmed (interests part: library evidence, see header) | backend/apps/api/serializers.py:222-223; consumer frontend/lib/features/answer/survey_answer_screen.dart:241-247 | `child=serializers.ListField(child=serializers.CharField()),` | Invalid item in `answers` or `interests` | `fields` is documented and typed as name to list of strings (API.md:141-143). For answers it is a list of objects. For a bad interest code it is an object keyed by index. The app depends on Dart's text form of the nested row, and a bad interest would print as raw `{0: [...]}`; the app cannot send one itself. | Document the nested shape and parse it as data in the app. |
| A-109 | Later | Confirmed | frontend/lib/widgets/open_text_field.dart:58; server backend/apps/api/serializers.py:163; label frontend/lib/features/answer/survey_answer_screen.dart:628 | `maxLength: maxOpenTextLength,` | An open answer near 2000 characters with emoji or Arabic diacritics | Flutter counts grapheme clusters (text_formatter.dart:542-543 in the SDK) and the server counts code points. The text passes in the app and fails with 400. Send then marks a filled answer "Needs an answer". | Count the same unit on both sides, and show the server's message. |
| A-110 | Later | Confirmed | frontend/lib/features/answer/survey_answer_screen.dart:277 | `'Your latest answers could not be saved. Cannot reach the server.',` | A draft PUT fails with a code that is not a block and not a network error (400, 500, unexpected response), then the user leaves | The dialog blames the connection although the server answered. | Show the real error message. |
| A-111 | Later | Confirmed | frontend/lib/features/auth/login_screen.dart:100; server backend/services/authentication_service.py:90 | `ApiException.invalidCredentials => 'Email or password is incorrect.',` | A suspended or deleted account logs in with the correct password | The server says "Account is suspended or deleted." The app replaces it with "Email or password is incorrect." A suspension demo would look like a wrong password. The server only reaches this message after the password check. | Show the server message, or use a distinct code. |
| A-112 | Later | Confirmed | frontend/lib/features/auth/register_screen.dart:118 | `await auth.login(email, _password.text);` | Register succeeds, then the login call is throttled or the network fails | The user stays on the form with an error. Pressing the button again gives "Email is already registered." | After a successful register, send the user to login on failure. |
| A-113 | Later | Likely (library evidence, see header) | backend/apps/api/views.py:130; hard delete is available at backend/apps/core/admin.py:16 | `return super().post(request, *args, **kwargs)` | A user row is deleted in Django admin while the app holds a valid refresh token | Refresh raises an unhandled DoesNotExist, so the server gives 500 instead of 401. The app shows "Unexpected server error." and keeps the tokens. Normal account deletion is soft and is not affected. | Treat a missing user on refresh as 401. |
| A-114 | Later | Confirmed | backend/apps/api/views.py:54 (also :81, :103, :136, :147, :160, :199, :365) | `responses={201: UserSerializer},` | Reading Swagger at /api/v1/docs/ | The schema lists only part of the errors in API.md: no 400 or 429 on register and login, no 401 or 403 on the me and profile calls, no 401 anywhere. | Declare the same errors as the table. |
| A-115 | Should | Question | frontend/android/app/src/debug/AndroidManifest.xml:6; statement planning/API.md:17 | `<uses-permission android:name="android.permission.INTERNET"/>` | Running on Android over http, or building a release APK | API.md says http needs `usesCleartextTraffic`, but no manifest under frontend/android sets it. The main manifest has no INTERNET permission, so a release build cannot reach the server. No emulator exists (CLAUDE.md), so the debug effect is unverified. Does the demo run on Chrome only? May duplicate Part 4. | Test on Android, then correct either the manifest or the document. |

Findings by severity: Blocker 1, Should 4, Later 11, Scope 0. Total 16.


---

# TASK-21 audit, Part 4: the Flutter app

Target: develop @ b77dbb3. Finding IDs A-150 to A-174.

**Read:** all 36 files of frontend/lib/, all 18 files of frontend/test/, frontend/pubspec.yaml, frontend/pubspec.lock (versions), documentation/design/README.md, .claude/skills/flutter-screen/SKILL.md (the token rule).
**Read to check whether behaviour is handled elsewhere:** backend/config/settings.py:112-186, backend/apps/api/exceptions.py, permissions.py, serializers.py, views.py (token views), backend/services/authentication_service.py:78-95, backend/tests/api/test_auth.py:150-302, frontend/android/app/src manifests, the flutter_secure_storage_web 2.1.1 source in the pub cache, Flutter SDK snack_bar.dart, scaffold.dart and dropdown.dart, and the Google Fonts CSS for IBM Plex Sans.
**Not run:** no flutter command and no test suite. Everything below comes from reading code. No rendered behaviour was observed.
**Not reached:** the requirement status board (planning/KANBAN.md names no FR status, and planning/ has no D-127 or UC-06 text), so "Done" is taken from the brief's wording.

## 1. Screen states (NFR-05)

| Screen | Loading | Error | Empty | Verdict |
|---|---|---|---|---|
| AuthGate, `frontend/lib/app.dart:89` | spinner :94 | none; every Exception becomes a silent login :76 | n/a | Gap, A-155 |
| LoginScreen, `features/auth/login_screen.dart:131` | button spinner :217 | FormMessage :210, field errors :171, :192 | n/a (form) | OK |
| RegisterScreen, `features/auth/register_screen.dart:152` | options spinner :163, button spinner :357 | options error with retry :176; submit FormMessage :350 | n/a (fixed lists) | OK |
| EligibleSurveysScreen, `features/surveys/eligible_surveys_screen.dart:133` | spinner :167 | StateMessage with retry :169-183 | StateMessage with action :186-206 | OK |
| ProfileScreen, `features/profile/profile_screen.dart:317` | skeleton :321 | `_LoadError` with retry :322, :700 | first-time hero, `profile_hero.dart:58` | OK |
| SurveyStartScreen, `features/answer/survey_start_screen.dart:163` | spinner :166 | error with retry :170; blocked :177 | n/a (publish requires a question, `services/survey_service.py:88`) | OK |
| SurveyAnswerScreen, `features/answer/survey_answer_screen.dart:306` | detail is passed in; sending state :673, :597 | block :316, snackbar :231, alert line :667, leave dialog :272 | n/a | OK |
| SurveySentScreen, `features/answer/survey_sent_screen.dart:49` | n/a (static) | n/a | n/a | OK |
| Answered surveys (UC-06) | no screen | no screen | no screen | Missing, A-150 |

## 2. Session, refresh and token trace

| Question | What the code does | Verdict |
|---|---|---|
| Where 401 is handled | One wrapper, `core/api/api_client.dart:60-64`, for every authenticated call | OK |
| 401 with an expired refresh token | Refresh answers 401 or 400 (:87), tokens cleared (:88), `SessionExpiredException` (:89). Every screen sends it to login with the notice | OK |
| Parallel 401s | Single flight through `_refreshing` (:26, :73). The check at :70 skips a refresh when another call already replaced the token. Tested at `api_client_test.dart:92` | OK, no refresh storm |
| Rotation (`settings.py:157-158`) | New refresh token is saved (:96-98). No test returns a rotated token, but the code is direct. Lost reply: A-162 | OK on the normal path |
| Late 401 after a failed refresh | Second caller retries with no token and gets `ApiException(401)` instead of SessionExpired. Both callers that can overlap use `Future.wait`, where the first error (SessionExpired) wins | No visible effect, not reported |
| Suspended account (`is_active=False`) | Access token gets 401, refresh gets 401 (`test_auth.py:293`), tokens cleared, login with "Your session ended". Next login: A-156 | Refused correctly |
| Suspended row that kept `is_active=True` | `IsRespondent` answers 403, no redirect | A-161 |
| Redirect and clearing | `pushAndRemoveUntil(... false)` at `eligible_surveys_screen.dart:118` and `profile_screen.dart:278`; tokens cleared in `api_client.dart:88`, and in `auth_repository.dart:96` on logout, in a `finally` | OK |
| Retried request keeps its body | `_request` is called again with the same body and timeout, :63 | OK |
| Mobile storage | `FlutterSecureStorage`, platform keystore | OK |
| Web storage | AES-GCM in localStorage with the raw key stored beside it (no `wrapKey` set, `token_store.dart:15`) | A-163 |
| Web session lifetime | Survives F5. `flutter run -d chrome` starts a fresh browser profile on a random port, so a new run starts logged out | Fact for the demo script |
| Secure context on web | `http://127.0.0.1` and localhost qualify; a LAN IP does not | A-165 |
| CORS for the demo | localhost and 127.0.0.1 on any port, DEBUG only, `settings.py:173-177` | OK while DEBUG is True |

## 3. Timeouts and the state left behind

Every call passes through `_request`: 15 s default (`api_client.dart:19`), 60 s for submit (`answer_repository.dart:10`). Timeout and connection failure both become `ApiException.network` (:122-123).

| Call | State after a timeout or no server | Verdict |
|---|---|---|
| AuthGate `me/` | Login with no message, up to 45 s of spinner when a refresh is involved | A-155 |
| Login | "Cannot reach the server. Is it running?", form enabled | OK |
| Register | Same message, but see A-160 when the account was created | OK / A-160 |
| Register options | Error with retry | OK |
| List | Error with retry | OK |
| Profile load | Error with retry | OK |
| Profile save | Snackbar with Try again, edits kept | OK / A-157 |
| Start load | Error with retry | OK |
| Delete draft | Snackbar, stays | OK |
| Draft autosave | Silent, retried at the next change | A-166 |
| Leave with a failed save | Dialog | OK / A-167 |
| Submit | Snackbar with Try again, answers kept, `_sending` reset | OK / A-168 |
| Logout | Tokens cleared after the wait, login opens | OK |
| Response body stalls after headers (mobile) | No timeout | A-164 |

## 4. Double taps

| Action | Location | Guard set before the first await | Button disabled | Verdict |
|---|---|---|---|---|
| Login | `login_screen.dart:56`, :216 | yes | yes | OK |
| Register | `register_screen.dart:84`, :356 | yes | yes | OK |
| Save profile | `profile_screen.dart:199`, :628 | yes | yes | OK |
| Save draft | `survey_answer_screen.dart:94-96` | single-flight queue | no button | OK |
| Submit answers | `survey_answer_screen.dart:173`, :672 | yes | **no**, `onPressed: _send` stays set; the guard makes it a no-op | Safe once sending, A-151 for the step before |
| Next, Skip, Review answers | `survey_answer_screen.dart:143` | **none** | no | A-151, A-159 |
| Logout | `eligible_surveys_screen.dart:79`, :155 | flag set synchronously | yes | OK |
| Delete draft | `survey_start_screen.dart:128`, :212 | flag set after a confirm dialog | yes | OK |
| Survey card, Start, Continue | `eligible_surveys_screen.dart:102`, `survey_start_screen.dart:83` | none | no | A route push covers the screen with a modal barrier; not reported |

## 5. `mounted` after await

Every await followed by context or setState was checked in login, register, list, profile, start, answer and sent screens. All have a guard. One path escapes because the callback outlives the screen:

| Location | Missing check | Finding |
|---|---|---|
| `features/profile/profile_screen.dart:200`, reached from the snackbar action at :256 | `setState` with no `mounted` check | A-157 |

`survey_answer_screen.dart:236` has the same shape, but `_close` and `_onPop` hide the snackbar first (:267, :297), so it is not reachable in normal use.

## 6. Stale navigation

| Scenario | What happens | Verdict |
|---|---|---|
| Back after submit | Answer route is replaced (:197); the Sent screen's PopScope goes to the list | OK |
| List after submit or profile edit | Reloads on return, `eligible_surveys_screen.dart:98`, :113 | OK |
| Resume a closed or already submitted survey | Start loads survey and draft; 409 becomes a block screen, `survey_parts.dart:47`, tested | OK |
| Survey closes while answering | Next PUT returns 409, block screen | OK |
| Logout | All routes removed | OK |
| Session end inside the answer flow | List guards with `isCurrent` (:113). `survey_start_screen.dart:98` and `eligible_surveys_screen.dart:98` only check `mounted`, so one extra unauthenticated reload can fire while the routes are being removed | No visible effect, not reported |
| Rating hint "1 is the lowest, 5 the highest" (`survey_answer_screen.dart:420`) | Server scale is fixed at 1 to 5, `question_service.py:20` | OK |

## 7. Answer flow state

| Topic | What the code does | Verdict |
|---|---|---|
| Position ring | Question n of m, full on the last question and the review, no ping (:333, :370). Matches D-118 | OK |
| Answers on Back | Kept in `_answers`, tested | OK |
| Rotation or window resize | State object survives | OK |
| Autosave | On every question change and on leave; no manual save; typing alone is not saved | A-166 |
| Failed autosave | Silent; `_goTo` ignores the result (:90) | A-166 |
| Local vs server draft | Whole-draft PUT, no version check | A-169 |
| Draft with removed question or option | Dropped by `keptFor`, `answer_models.dart:145` | OK |
| Required messages | Choice and text wording, marked controls, tested | OK |
| Last question | "Review answers", never Skip | OK, but A-151 |
| Controllers and subscriptions | login :50-51, register :75-77, profile :103-104, open text :43, skeleton `_pulse` :296, ring `_ping` :94; no stream subscriptions | All disposed |

## 8. Text input direction

The app has no locales or flutter_localizations, so ambient `Directionality` is always LTR. No screen wraps a subtree in `Directionality`.

| Field | Location | textDirection | Verdict |
|---|---|---|---|
| Login email | `login_screen.dart:163` | ambient LTR | Correct for an email |
| Login password | `login_screen.dart:183` | ambient LTR | Correct |
| Register name | `register_screen.dart:216` | none | **Gap, A-170** |
| Register email | `register_screen.dart:229` | ambient LTR | Correct |
| Register password | `register_screen.dart:249` | ambient LTR | Correct |
| Register age | `register_screen.dart:273` | ambient LTR | A-171 |
| Profile age | `profile_screen.dart:435` | ambient LTR | A-171 |
| Open answer | `widgets/open_text_field.dart:56` | `directionOf(text)` :62; default `TextAlign.start` follows it | Correct, tested |

## 9. Semantics

| Item | Location | Verdict |
|---|---|---|
| Password toggles | `login_screen.dart:194`, `register_screen.dart:259` | tooltip |
| Profile, Log out | `eligible_surveys_screen.dart:139`, :144 | tooltip |
| Back, Leave survey | `survey_answer_screen.dart:337`, :342 | tooltip |
| Close | `survey_sent_screen.dart:60` | tooltip |
| Ring painter | `signal_ring.dart:113` | Semantics label around ExcludeSemantics |
| Ring in app bar and draft hero | `survey_answer_screen.dart:368`, `survey_start_screen.dart:325` | Excluded on purpose; the same fact is in adjacent text |
| Hero circles | `profile_hero.dart:112` | Excluded, decorative |
| Answer and rating controls | `answer_option.dart:38`, `rating_scale.dart:92` | Label, checked, group |
| Spinners | see A-173 | No label |

## 10. Values outside lib/theme (SKILL.md rule 1)

No `Color(0x..)`, `Colors.*`, `fontFamily`, or literal `Duration` for motion appears in feature or widget code. Numeric literals that break the rule:

| Location | Value |
|---|---|
| `widgets/state_message.dart:16-17` | icon circle 56, icon 28 |
| `widgets/signal_ring.dart:19` | default size 88 (duplicates `SsLayout.ringSize`) |
| `widgets/signal_ring.dart:52-53` | ping gap 8, ping stroke 2 |
| `widgets/signal_ring.dart:103` | track alpha 0.18 |
| `widgets/signal_ring.dart:108-109` | threshold 48, `fontSize: 12`, `height: 16 / 12` |
| `widgets/signal_ring.dart:161`, :163 | opacity 0.35, scale 0.15 |
| `widgets/open_text_field.dart:59-60` | 5 lines |
| `features/answer/survey_answer_screen.dart:18` | opacity 0.55 |
| `features/profile/profile_hero.dart:269` | opacity 0.5 |

## 11. Force-unwraps and casts on server data

All model `as` casts run inside a repository `_parse` or a `try` that maps `TypeError` (and `FormatException` for answers) to `unexpected_response`: `answer_repository.dart:67-82`, `profile_repository.dart:35-44`, `surveys_repository.dart:16-23`, `auth_repository.dart:78`. `RespondentProfile.age` and `gender` are non-null, and the region and interests columns were mapped to codes by migration 0004, so the dropdown's "exactly one item" assertion is not reachable.

| Location | Expression | Verdict |
|---|---|---|
| `survey_answer_screen.dart:655` | `question.ratingValues.last` | Safe: rating answers exist only on rating questions unless a published question changes type |
| `survey_answer_screen.dart:656` | `options.firstWhere` | Safe: `keptFor` drops unknown options |
| `survey_answer_screen.dart:370` | `position * 100 / total` | Safe: publish requires one question |
| `survey_start_screen.dart:54-55`, :91, :102-103, :179, :183 | `_detail!`, `_draft!`, `_block!`, own-future casts | Guarded by phase |
| `profile_screen.dart:116`, :160, :266, :353 | `_options!`, own-future cast, key lookup | Guarded by phase or by construction |
| `register_screen.dart:113-115` | `int.parse`, `_gender!`, `_region!` | Validated just above |

## 12. Findings

### A-150
| Field | Content |
|---|---|
| Severity | Blocker |
| Confidence | Confirmed |
| Location | frontend/lib/features/surveys/surveys_repository.dart:12 |
| Quote | `final json = await _api.get('surveys/eligible/');` |
| Trigger | A respondent wants to see the surveys already answered. No file under frontend/lib/ calls `me/responses/`, and the app bar offers only profile and logout (`eligible_surveys_screen.dart:137-157`). |
| Effect | UC-06 does not exist in the app, while the API (`backend/apps/api/views.py:370`) and the web (`backend/apps/responses/urls.py:15`) both have it. The advisor's suspicion is confirmed. A submitted survey disappears, and the Sent screen says it "is no longer in your list". FR-01 "covering everything the current respondent web pages offer" cannot be claimed Done. |
| Fix direction | Add an answered-surveys screen on `GET /me/responses/`, or record the deferral and narrow the FR-01 claim. |

### A-151
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:672 |
| Quote | `onPressed: _send,` |
| Trigger | Double-click or double-tap "Review answers" (or "Back to review"). The first tap moves to the review on the next frame. The bottom bar switches with no animation, and the full-width "Send answers" sits exactly where the tapped button was. `_advance` has no guard. |
| Effect | The second tap sends the response without the respondent ever seeing the check screen. The send cannot be undone ("You can't change your answers after you send them"). A mouse double-click in the Chrome demo is enough. |
| Fix direction | Ignore Send for a short period after the review appears, or ask for a confirmation. |

### A-152
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:450 |
| Quote | `question.text,` |
| Trigger | A provider writes a survey in Arabic. Only the typed open answer and its review row use `directionOf`. Question text, option labels (`answer_option.dart:68`), survey titles and descriptions (`eligible_surveys_screen.dart:289`, :293, `survey_start_screen.dart:282`, :287, :340), and the user name in the app bar (`eligible_surveys_screen.dart:136`) all use the ambient LTR direction. |
| Effect | Arabic questions are left-aligned, and trailing punctuation such as the question mark lands on the wrong side. The seed data has no Arabic, so this appears only if an Arabic survey is authored for the demo. |
| Fix direction | Apply `directionOf` to every server-authored text. |

### A-153
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/theme/app_theme.dart:41 |
| Quote | `static TextStyle get body => GoogleFonts.ibmPlexSans(` |
| Trigger | Any Arabic text in the heading, body, label or caption styles, which covers question text, options and the open answer field. The Google Fonts CSS for IBM Plex Sans lists Cyrillic, Greek, Vietnamese and Latin subsets only. Arabic is a separate family, `ibmPlexSansArabic`, available in the same package and not used. No `fontFamilyFallback` is set. |
| Effect | NFR-05 "Arabic-capable fonts" holds only for the Readex Pro styles. Arabic reading text falls back to whatever the platform supplies, so it does not match the design type. |
| Fix direction | Use IBM Plex Sans Arabic as a fallback family on the reading styles. |

### A-154
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Question |
| Location | frontend/pubspec.yaml:37 |
| Quote | `google_fonts: ^8.2.1` |
| Trigger | The demo laptop has no internet access. No font is bundled (the assets and fonts sections of pubspec.yaml are commented out), so every font is fetched at runtime. |
| Effect | The theme fonts are replaced by defaults. Chrome's fallback for Arabic glyphs is probably fetched from the network as well, so Arabic may not render at all. Will the demo room have internet? |
| Fix direction | Bundle the font files as assets and turn off runtime fetching. |

### A-155
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/app.dart:76 |
| Quote | `} on Exception {` |
| Trigger | The app starts with a stored session while the server is off or slow. |
| Effect | After up to 45 s of spinner the respondent sees the login form with no explanation, as if logged out. The tokens remain stored. NFR-05 says every screen has an error state; this one has none. `LoginScreen.notice` exists but is not passed. |
| Fix direction | Separate network failure from an ended session and show an error with retry. |

### A-156
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/login_screen.dart:100 |
| Quote | `ApiException.invalidCredentials => 'Email or password is incorrect.',` |
| Trigger | A suspended respondent logs in with the correct password. The API answers 401 `invalid_credentials` with "Account is suspended or deleted." (`backend/services/authentication_service.py:90`, `backend/apps/api/exceptions.py:32`). |
| Effect | The app discards the server's message and says the password is wrong. A committee watching a suspension demo sees a false reason. |
| Fix direction | Show the server message, or give suspended accounts their own code. May duplicate Part 3 if the code is split. |

### A-157
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/lib/features/profile/profile_screen.dart:256 |
| Quote | `action: SnackBarAction(label: 'Try again', onPressed: _save),` |
| Trigger | A profile save fails, then the respondent leaves with Discard. In this SDK a snackbar with an action persists (`snack_bar.dart:303`), and it lives on the app-level messenger. The profile screen does not hide it on leaving, unlike the answer flow. |
| Effect | "Not saved. Try again" stays over the survey list indefinitely. Tapping it calls `_save` on a disposed State, and `setState` at :200 throws. Nothing is saved. |
| Fix direction | Hide the snackbar when the screen is left. |

### A-158
| Field | Content |
|---|---|
| Severity | Should |
| Confidence | Confirmed |
| Location | frontend/android/app/src/main/AndroidManifest.xml:1 |
| Quote | `<manifest xmlns:android="http://schemas.android.com/apk/res/android">` |
| Trigger | A release APK is built. The INTERNET permission exists only in the debug and profile manifests. |
| Effect | A release build of the "mobile app" in FR-01 cannot reach the API, so every screen shows the network error. CLAUDE.md records no emulator or AVD, so the Android path looks unexercised. The Chrome demo is not affected. |
| Fix direction | Declare INTERNET in the main manifest and run the app once on Android. |

### A-159
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:143 |
| Quote | `void _advance() {` |
| Trigger | Double-tap Next. The button stays in the same place on the next question, and nothing ignores the second tap. |
| Effect | An optional unanswered next question is silently skipped. A required one shows its error before the respondent has read it. |
| Fix direction | Ignore advances while a page transition runs. |

### A-160
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/register_screen.dart:118 |
| Quote | `await auth.login(email, _password.text);` |
| Trigger | Register succeeds, then the automatic login fails (network or 429), or the register reply times out after the account was created. |
| Effect | The form stays open with an error. Tapping Create account again gives "Email is already registered." although the respondent has never logged in. |
| Fix direction | After a successful register, send a login failure to the login screen with a notice. |

### A-161
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/core/api/api_client.dart:60 |
| Quote | `if (response.statusCode == 401 && authenticated) {` |
| Trigger | A row with `account_status` SUSPENDED and `is_active=True` (rows older than F-18, per `test_auth.py:174`) passes JWT and gets 403 `permission_denied`. Only `currentUser` handles 403. |
| Effect | The list shows "Only active respondents can use this endpoint." with a Try again that never works. There is no redirect, and the tokens stay. |
| Fix direction | Treat `permission_denied` from any call as an ended session. |

### A-162
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/core/api/api_client.dart:87 |
| Quote | `if (response.statusCode == 401 \|\| response.statusCode == 400) {` |
| Trigger | With rotation and blacklist on (`settings.py:157-158`), the refresh reply is lost after the server rotated the token, or two browser tabs refresh at once. Single flight works per tab only. |
| Effect | The next refresh presents a blacklisted token, the app clears the session and the respondent is logged out. Answers since the last save point are lost. |
| Fix direction | Accept the risk on record, or add a short reuse grace period on the server. |

### A-163
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/core/api/token_store.dart:12 |
| Quote | `/// Keeps tokens in the platform keystore (encrypted browser storage on web).` |
| Trigger | The Chrome build. With no `wrapKey` configured, the package stores the raw AES key in localStorage next to the ciphertext (`flutter_secure_storage_web.dart:182-191`). |
| Effect | Any script running on the page can decrypt the 7-day refresh token. "Secure storage" is true on mobile only and must not be claimed for the web demo. |
| Fix direction | Correct the comment and the claim; keep web as a development target. |

### A-164
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/core/api/api_client.dart:121 |
| Quote | `return await http.Response.fromStream(streamed);` |
| Trigger | On mobile, headers arrive and then the body stalls. The timeout at :120 covers only `send`. |
| Effect | The screen stays in its loading state with no limit. |
| Fix direction | Apply the timeout to reading the body as well. |

### A-165
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/login_screen.dart:89 |
| Quote | `} on ApiException catch (error) {` |
| Trigger | Token storage fails with something other than an `ApiException`, for example the web build served from a plain-http LAN address, where the package throws `UnsupportedError` (`flutter_secure_storage_web.dart:30`). |
| Effect | The login button spins forever. The same class of failure leaves `app.dart:66` (outside its `try`) on an endless spinner, and the profile skeleton stays up. |
| Fix direction | Catch storage failures in `ApiClient` and report them as a typed error. |

### A-166
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_start_screen.dart:390 |
| Quote | `title: 'Saved as you go',` |
| Trigger | The respondent answers the current question, then closes the tab, presses F5 or the app is killed. Saves happen only on question change and on leave. A failed save gives no sign either (`survey_answer_screen.dart:90`, tested as silent). |
| Effect | The current answer is lost, and after a server outage everything since the last good save is lost, while the screen promised answers are kept. FR-06's save and resume does work through the normal leave path. |
| Fix direction | Debounce a save after each change, and show a small "not saved" sign when one fails. |

### A-167
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:277 |
| Quote | `'Your latest answers could not be saved. Cannot reach the server.',` |
| Trigger | A draft save fails with 400, 429 or 500 and the respondent leaves. |
| Effect | The dialog blames the connection even though the server answered. |
| Fix direction | Use a neutral sentence, or the API message. |

### A-168
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/survey_answer_screen.dart:211 |
| Quote | `if (error.code == 'duplicate_response' && _networkFailed) {` |
| Trigger | A send times out but is stored by the server (K-02). The respondent edits an answer on the review and sends again, which returns 409. The same path fires if the first send never arrived and the survey was answered on another device. |
| Effect | "Answers sent" appears with the edited count and the current time, while the server holds the first version. |
| Fix direction | Lock edits after a failed send, or show the already-answered screen when the answers changed. |

### A-169
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/answer/answer_repository.dart:43 |
| Quote | `await _api.put('surveys/$id/draft/', body: _answersBody(answers));` |
| Trigger | The same respondent answers the same survey in two tabs or on two devices. The PUT replaces the whole draft with no version check. |
| Effect | The last save silently overwrites the other one. |
| Fix direction | Accept on record for Increment 1, or send `updated_at` and refuse stale saves. |

### A-170
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/register_screen.dart:216 |
| Quote | `TextFormField(` |
| Trigger | A respondent types an Arabic name. The field sets no `textDirection`, unlike the open answer field. |
| Effect | The Arabic name is left-aligned, and mixed text or punctuation can appear out of order. |
| Fix direction | Use `directionOf` on the name field. |

### A-171
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Likely |
| Location | frontend/lib/features/auth/register_screen.dart:278 |
| Quote | `inputFormatters: [FilteringTextInputFormatter.digitsOnly],` |
| Trigger | A keyboard that produces Arabic-Indic digits. The same formatter is at `profile_screen.dart:440`. `digitsOnly` keeps only 0-9. |
| Effect | The digits are dropped with no message and the age stays empty. |
| Fix direction | Convert Arabic-Indic digits to ASCII in the formatter. |

### A-172
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/widgets/state_message.dart:16 |
| Quote | `static const double _iconCircle = 56;` |
| Trigger | Project rule 1 in flutter-screen/SKILL.md: no numeric size literals outside tokens. All nine places are listed in section 10. |
| Effect | Not visible to a user. The claim "design tokens only" is not strictly true. |
| Fix direction | Move these values into `SsLayout` and `SsMotion`. |

### A-173
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/auth/login_screen.dart:221 |
| Quote | `child: CircularProgressIndicator(` |
| Trigger | A screen reader during loading. The same applies at `register_screen.dart:163`, :361, `profile_screen.dart:633`, `eligible_surveys_screen.dart:167`, `survey_start_screen.dart:168` and `app.dart:94`. |
| Effect | Loading is not announced, and a submitting button loses its name. Only the profile skeleton has a label. |
| Fix direction | Give the indicators a `semanticsLabel`. |

### A-174
| Field | Content |
|---|---|
| Severity | Later |
| Confidence | Confirmed |
| Location | frontend/lib/features/profile/profile_screen.dart:332 |
| Quote | `canPop: !content \|\| !_dirty,` |
| Trigger | The respondent presses back while a save is running and picks Discard. |
| Effect | The dialog says the edits will be lost, but the save completes on the server. |
| Fix direction | Block leaving while `_saving` is true. |

## Counts

Blocker 1, Should 8, Later 16, Scope 0. Total 25.


---

# TASK-21 audit, Part 5: data and history (develop @ b77dbb3)

**Read:** backend/apps/core/migrations/0001 to 0006 (whole), backend/apps/core/models/ (whole), backend/repositories/ (whole), backend/services/ except health_service.py, planning/BACKEND_AUDIT.md (whole), audit notes checks.md, backend/apps/core/management/commands/seed_demo_data.py (current, and its region and interests lines at c762367^), backend/apps/core/admin.py, backend/apps/api/exceptions.py, backend/apps/analysis/views.py, backend/infrastructure/huggingface_client.py, the first 60 lines and line 215 of backend/config/settings.py, and git history of these paths.

**Method for (b):** the pure functions `map_region` and `map_interests` of 0004 were executed on sample strings with Django stubbed out and no database. Every "maps to" result in section (b) is real output. The temporary script was deleted afterwards.

**Not reached:**
- The real contents of the team's database. Querying it is forbidden, so which rows exist and whether the seed was re-run after 0004 is unknown (see A-203).
- backend/.env, so the effective HF URL, token and USE_CELERY value are unknown (see A-207, A-209).
- docs/**, denied by project settings. The number of ignored files under docs/ at b77dbb3 is not stated here. The figure of 79 in BACKEND_AUDIT is the document's own and was not re-verified.
- The app, the web templates and the API views beyond the lines cited.

## (a) Migrations 0001 to 0006

Every migration uses the default `atomic = True`, so on PostgreSQL each one is its own transaction. 0003, 0004 and 0005 are three separate transactions on purpose (0003:1), which avoids PostgreSQL's "pending trigger events" error when rows are updated and a table is altered together.

| Migration | What it does | Reverse (`migrate core <previous>`) | Risk on non-empty data |
|---|---|---|---|
| 0001_initial | Creates all tables; `unique_response_per_survey_respondent` (survey, respondent). | Works; drops every table, and Django also unapplies apps that depend on the user model (admin, token_blacklist). Total data loss, expected for an initial migration. | None forward. |
| 0002 | 10 indexes; `unique_answer_per_response_question` (response, question). | Works; no row data involved. | Forward fails only if an answer is duplicated per response and question. `_build_answer_map` (response_service.py:242) already rejected that at service level. Low. |
| 0003 | Adds education, occupation, marital_status (default ""), temporary interests_codes array; gives old interests text a default. | Works; the four added columns are dropped, so their values are lost. Expected. | None. Reverse of 0005 depends on the default added here (0003:78). |
| 0004 | Data only. RunPython(forward, reverse) maps free text to codes. | `reverse_code` exists and runs, but does **not** restore the original text. **Finding A-211.** | High. Unmapped values are erased or turned into "no restriction". **Findings A-200, A-201, A-202, A-203.** |
| 0005 | Drops old interests text; renames interests_codes to interests; narrows both region columns from 255 to 32 characters. | Works; re-adds interests as empty text (filled by reversing 0004), widens the columns. | Original interests text is destroyed here for good. Cannot fail on what 0004 left, see (b). |
| 0006 | Adds nullable Response.started_at; creates response_drafts with `unique_draft_per_survey_respondent`. | Works; drafts and started_at values are lost. Expected. | None. Old responses keep started_at NULL. |

## (b) 0004 on non-empty data, traced

Column state on entry (after 0003): `respondent_profiles.region` varchar(255) NOT NULL, `interests` text NOT NULL, `survey_targeting_criteria.region` varchar(255) NULL.

| Line | Behaviour |
|---|---|
| 94, 100 | `normalise` casefolds and removes whitespace, hyphen and the two apostrophes. It does not strip Arabic diacritics, does not unify Arabic letter forms, and does not remove direction marks. Comparison is whole-string. |
| 106 to 107 | Alias table per code: the code, the English label, and the listed extras. Matching a code again gives the same code, so the mapping is idempotent. |
| 134 | `.all()` loads every profile into memory. No iterator and no batching; one UPDATE per row. Not a concern at this project's size. |
| 135 to 138 | Profile region. Unmapped gives `code or ""`: **the original text is overwritten** and no copy is kept anywhere. |
| 139 | Interests are written to interests_codes. Only English keywords exist (lines 66 to 92). Unknown words are dropped. |
| 140 | `update_fields` leaves `updated_at` unchanged. Correct. |
| 143 to 148 | Targeting region. NULL and "" rows are skipped. Unmapped gives `criteria.region = None`, which the service reads as **no region restriction**. |
| 150 to 153 | The only trace is a printed count of regions. Which rows were affected is not shown. **Interest losses are not counted at all.** |

| Input (real output of the functions) | Result |
|---|---|
| Nulls | Impossible for profile columns (NOT NULL). Function returns None or [] without crashing. |
| "" and "   " | None, counted as "not mapped", profile stored as "". No crash. |
| "Damascus", " damascus ", "DAMASCUS", "دمشق", "حلب", "ادلب", "إدلب", "حماه", "حماة", "ريف دمشق", "Rural Damascus", "Deir-ez-Zor", "Dara'a", "Ar Raqqa", "السويداء" | Correct code. Case, spaces and hyphens are handled. |
| "Amman", "Beirut", "Germany" | None. Foreign places do **not** become OUTSIDE_SYRIA; they are erased. |
| "damascus, syria", "Damascus Governorate", "محافظة دمشق" | None. Whole-string compare fails. |
| "Edlib", "Alep", "Hims", "Dar'a", "Al-Sweida", "Al-Raqqa", "Damascus Rural", "Dayr az Zawr" | None. Common spellings missing. |
| "أدلب", "السويدا", "حما", "دِمَشق", "دمشق" followed by U+200F | None. Arabic variants missing. |
| Interests "Technology, Education" | [TECHNOLOGY, EDUCATION] |
| Interests "customer experience, digital services", "programming, reading", "technologies", "Football", "AI and science", "تكنولوجيا، رياضة", "التعليم" | [] |

**Can 0005 fail on what 0004 left?** No. After 0004 every profile region is a code or "" and every targeting region is a code, NULL or "", all at most 13 characters, so narrowing to varchar(32) succeeds. 0005 adds no NOT NULL. `choices` and `blank` are not database constraints, so "" stays stored. Interests rows are valid arrays.

**Crash behaviour:** no input traced raises. A database failure rolls back the whole of 0004 (one transaction). A failure in 0005 leaves 0004 committed, and re-running continues at 0005.

**Consequence for respondents:** `is_complete()` (respondent_profile.py:102 to 107) needs a valid governorate and at least one interest. An unmapped row makes `get_eligible_survey_items` return [] (survey_service.py:161) and `match_respondent_to_survey` return False (targeting_service.py:55), so the API refuses the survey with 403. Nothing tells the user why.

**The seeded demo database for 2026-11-15:**
- 0004 and the seed rewrite both arrived in c762367 (2026-11-07). The seed before that commit wrote region "Amman" for the profile and the targeting row, and interests "customer experience, digital services".
- Migrated and **not** re-seeded: respondent@demo.com gets region "" and interests [], completion 2 of 7 (29%), and sees no surveys. The demo survey's region becomes NULL, so it is open to every governorate.
- Migrated and re-seeded: seed_demo_data restores Damascus and two interests (completion 4 of 7, 57%) and the Damascus targeting. It only repairs the three demo accounts and the one demo survey. Any other respondent or survey typed in by hand stays erased.
- Fresh database: the seed writes valid codes and 0004 has nothing to change.
- In every case the seeded respondent has already answered the only seeded survey. See A-204.

## (c) Constraints, deletes, indexes, model state

**Model state against migrations:** `makemigrations --check --dry-run` printed "No changes detected" (checks.md). Reading the models against 0001 to 0006 agrees. Requirements pin Django 5.2.19 and psycopg 3.1.18.

| Rule the service relies on | Database object | Service use | Verdict |
|---|---|---|---|
| One response per respondent per survey | `unique_response_per_survey_respondent` (survey, respondent), 0001:177, response.py:27 to 30 | response_service.py:117 tests that exact name, raises DuplicateResponse; apps/api/exceptions.py:20 maps it to 409 | Names match. The IntegrityError is caught outside the atomic block (:115), so the rollback is clean. NFR-03 holds at service level. |
| One answer per question per response | `unique_answer_per_response_question`, 0002:55 | Pre-check at response_service.py:242; a violation re-raises | Correct. |
| One draft per respondent per survey | `unique_draft_per_survey_respondent`, 0006:32, response_draft.py:26 to 29 | response_service.py:158 tests that exact name, then re-reads and overwrites | Names match. Drafts of a survey that later closes stay in the table; harmless. |
| Unique email | Django-generated name starting `users_email` (0001:32) | authentication_service.py:38 and :77 test the substring | Works. Case differences are handled by lowercasing at :96. |

| Foreign key | on_delete | Effect |
|---|---|---|
| Survey.provider | CASCADE | Deleting a provider deletes all their surveys and other people's responses. |
| Response.survey, Response.respondent | CASCADE | Deleting a survey or respondent deletes the responses. |
| Answer.response, Answer.question | CASCADE | Follows. |
| Answer.selected_option | SET_NULL | Answer survives with no option. |
| ResponseDraft.survey, .respondent | CASCADE | Follows. |
| SentimentAnalysisResult.answer, TargetingCriteria.survey, RespondentProfile.user, QuestionOption.question, Question.survey | CASCADE | Follows. |

Hard-delete routes: `SurveyService.delete_survey` for DRAFT or CLOSED surveys (A-219), and Django admin at `/admin/`, where User is registered (apps/core/admin.py:16), for superusers only. `UserRepository.delete` has no caller outside tests. `AdminService.delete_account` is a soft delete.

| List query | Supporting index | Verdict |
|---|---|---|
| find_eligible_for_respondent | surveys_status_pub_idx; unique (survey, respondent) for NOT EXISTS; FK index on questions.survey | Covered. |
| ResponseRepository.find_by_respondent_id | responses_resp_sub_idx | Covered. |
| find_by_survey_id (responses, questions, answers, results) | FK indexes and unique (survey, respondent) | Covered. |
| count_submitted_by_date, count_created_by_date | responses_sub_at_idx, users_created_at_idx | Covered. |
| count_by_user_type, count_by_status | users_user_type_idx, surveys_status_idx | Covered. |
| DraftRepository.find | unique (survey, respondent) | Covered. |
| find_by_provider_id | FK index | Covered, but no ordering (A-220). |
| UserRepository.list_all | none needed | No ordering (A-220). |
| find_by_email, email_exists (`iexact`) | none usable; compares UPPER(email) | Sequential scan. No finding at this data size. |
| find_most_active | whole-table aggregate | Acceptable at this size. |

The eligibility rule exists twice, as ORM filters (survey_repository.py:30 to 48) and in Python (targeting_service.py:129 to 143). They were compared clause by clause and are equivalent, so there is no finding.

## (d) Every BACKEND_AUDIT finding at b77dbb3

The hashes in the document's fix log are not ancestors of b77dbb3 (A-221). "Fixed" below names the commit on develop's history that introduced the change, found with `git log -S`.

| ID | State | Commit | Evidence or reason |
|---|---|---|---|
| F-01 | Fixed | 5abef48 | backend/services/response_service.py:86 `with transaction.atomic():` |
| F-02 | Fixed | 5abef48 | backend/services/authentication_service.py:62 `with transaction.atomic():` |
| F-03 | Open, partly done | on_commit 5abef48, Celery option a8c1bb2 | response_service.py:111 on_commit; still synchronous by default. A-207 |
| F-04 | Open | none | .gitignore:23 `docs/`. A-210 |
| F-05 | Open, cannot be settled from code | none | Client URL and token come from the environment. A-209 |
| F-06 | Fixed | 7f00596 | docker-compose.yml:11 `"5432:5432"`. Removal of the old container not verifiable. |
| F-07 | Fixed | 5abef48 | analysis_service.py:41 `@transaction.atomic`; question_service.py:102 `with transaction.atomic():`. Side effect: A-208 |
| F-08 | Fixed | c762367 | targeting_service.py:118 `if region is not None and region not in Governorate.values:`; 8be4e40's trim and casefold was replaced by fixed codes. |
| F-09 | Fixed | 5abef48 | analysis_service.py:70 `self._ensure_survey_owner(provider_user, survey_id)`; question_service.py:134 |
| F-10 | Fixed for the API | 34630f0 | apps/api/exceptions.py:19 `core_exceptions.UnauthorizedAction: (403, "unauthorized_action"),`. Web pages still redirect, which the finding did not ask to change. |
| F-11 | Obsolete | none | Toolchain observation, not code. CLAUDE.md records it as not reproducible. Not re-run. |
| F-12 | Fixed | 9241d27 | CLAUDE.md:73 defines K-04. |
| F-13 | Obsolete | none | The report draft in documentation/graduation-1 no longer has the 163 claim; it now states 259 test functions at the end of Iteration 0. |
| F-14 | Fixed | 5abef48 | repositories/user_repository.py:27 is the only `def save(self, user):` |
| F-15 | Fixed | 5abef48 | config/settings.py:17 `raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")` |
| F-16 | Fixed | 5abef48 | apps/users/views.py:115 `@require_POST` |
| F-17 | Fixed | 5abef48 | infrastructure/huggingface_client.py:61 `f"Hugging Face request failed with HTTP {status_code}."` |
| F-18 | Fixed | 5abef48 | apps/core/models/user.py:80 and :85 `self.is_active = False` |
| F-19 | Fixed | 5abef48, then c762367 | repositories/survey_repository.py:47 `Q(criteria__region=profile.region)` compares fixed codes, so the " damascus " case cannot occur. |
| F-20 | Fixed | 5abef48 | services/survey_service.py:98 `< self.MIN_CHOICE_OPTIONS` |
| F-21 | Open | none | A-212 |
| F-22 | Open, latent | none | A-213 |
| F-23 | Fixed | a8c1bb2 | services/profile_service.py:87 `if type(age) is not int or age < self.MIN_AGE or age > self.MAX_AGE:` |
| F-24 | Open, latent | none | A-214 |
| F-25 | Open | none | A-215 |
| F-26 | Fixed | a8c1bb2 | services/authentication_service.py:96 `.lower()`; repositories/user_repository.py:19 `email__iexact` |
| F-27 | Fixed | a8c1bb2, narrowed by 920d0ec | services/response_service.py:117 |
| F-28 | Open | none | A-216 |
| F-29 | Fixed | a8c1bb2 | services/survey_service.py:66 `if not isinstance(title, str) or not title.strip():` |
| F-30 | Fixed | a8c1bb2 | apps/core/models/targeting_criteria.py has no `matches` method. |

| Known issue | Real state at b77dbb3 |
|---|---|
| K-01 | **Fixed** (5abef48), response_service.py:86. CLAUDE.md:70 is stale. |
| K-03 | **Fixed** (c762367). Line 141 of targeting_service.py still uses `!=`, but on validated codes, not free text. CLAUDE.md:72 is stale. Old rows: A-200, A-201. |
| K-04 | **Open.** Interests are stored but no targeting code reads them. A-217. |
| K-06 | **Open.** .gitignore:23. A-210. |
| K-12 | **Fixed** (5abef48). The check is in analysis_service.py:70. apps/analysis/views.py:16 still calls get_provider_survey to fetch the title, which is not the only guard. CLAUDE.md:78 is stale. |

## Findings

| ID | Severity | Confidence | Location | Quote | Trigger | Effect | Fix direction |
|---|---|---|---|---|---|---|---|
| A-200 | Should | Confirmed | backend/apps/core/migrations/0004_map_profile_lists.py:138 | `profile.region = code or ""` | Migrating a profile whose region matches no alias, such as "Amman", "Edlib" or "محافظة دمشق". | The original region is erased with no copy. The respondent silently loses every survey until they edit their profile. | Keep the original text in a backup column or report the affected rows, and widen the aliases before anyone migrates real data. |
| A-201 | Should | Confirmed | backend/apps/core/migrations/0004_map_profile_lists.py:147 | `criteria.region = code` | Migrating a survey targeted at a region that matches no alias. | The restriction becomes NULL, so a survey meant for one place is offered to every governorate, and only a count is printed. | Close or flag those surveys instead of turning an unknown region into no restriction. |
| A-202 | Should | Confirmed | backend/apps/core/migrations/0004_map_profile_lists.py:123 | `code = INTEREST_KEYWORDS.get(word.casefold())` | Migrating interests written in Arabic or using words outside the English keyword list. | Those interests vanish with no count, and 0005 then drops the text. A profile left with [] is treated as incomplete and sees no surveys. | Add Arabic keywords, report unmapped interests, and do not let a failed interest mapping remove eligibility. |
| A-203 | Blocker | Question | backend/apps/core/migrations/0004_map_profile_lists.py:138 | `profile.region = code or ""` | The team's database was seeded before c762367 ("Amman"), then migrated, and seed_demo_data was not re-run. | respondent@demo.com shows 29% completion and no surveys, and the demo survey loses its region. Team must confirm the database state. | Re-run the seed after migrating and check the demo accounts before 2026-11-15. |
| A-204 | Blocker | Confirmed | backend/apps/core/management/commands/seed_demo_data.py:81 | `response = self._upsert_response(survey, respondent)` | Logging in as respondent@demo.com on seeded data and opening the survey list. | The only seeded survey is already answered, so survey_repository.py:61 excludes it. The list is empty and the answer and draft flows cannot be shown without extra data. | Seed at least one more published, matching, unanswered survey. |
| A-205 | Should | Confirmed | backend/apps/core/management/commands/seed_demo_data.py:237 | `result.sentiment_label = SentimentLabel.POSITIVE` | Opening analytics for the seeded survey. | A hard-coded COMPLETED, POSITIVE, 0.95 result appears as if the model produced it, even when the Hugging Face call fails. | Tell the committee this row is seeded, or produce it through the real analysis path. |
| A-206 | Should | Confirmed | backend/apps/core/management/commands/seed_demo_data.py:111 | `user.account_status = AccountStatus.ACTIVE` | Suspending a demo account in rehearsal, then re-running the seed to reset. | Status reads ACTIVE but is_active stays False. Login passes authenticate_user, then apps/api/permissions.py:17 and the web session refuse the user. | Have the seed also restore is_active. |
| A-207 | Should | Confirmed | backend/services/response_service.py:192 | `self.analysis_service.analyze_open_text_answers(response_id)` | Submitting open-text answers with USE_CELERY unset (config/settings.py:215 defaults to false). | The request waits for Hugging Face, up to 15 seconds per open-text answer, before the respondent gets a reply. K-02 and F-03 remain partly open. Local USE_CELERY value not read. | Run analysis in the background by default, or state the synchronous limit. |
| A-208 | Later | Confirmed | backend/services/analysis_service.py:41 | `@transaction.atomic` | Any analysis run with open-text answers. | One database transaction stays open during every external HTTP call, and PENDING rows are never visible to other readers. May duplicate another part. | Keep the HTTP calls outside the transaction and commit per result. |
| A-209 | Blocker | Question | backend/services/analysis_service.py:62 | `result.mark_failed()` | Real submissions if the Hugging Face account still returns HTTP 402 as it did on 2026-10-23; backend/.env.example:15 also still names the older api-inference host. | Every open-text answer is marked FAILED and real sentiment counts stay zero, with no visible error. Current credentials could not be checked. | Run one real analysis call before the demo and record the result. |
| A-210 | Should | Confirmed | .gitignore:23 | `docs/` | Cloning the repository. | Nothing under docs/ is versioned, so project material kept there exists only on the one laptop. K-06 and F-04 remain open. | Move material worth keeping to a tracked folder or narrow the rule. |
| A-211 | Later | Confirmed | backend/apps/core/migrations/0004_map_profile_lists.py:161 | `profile.region = GOVERNORATE_LABELS.get(profile.region, profile.region)` | `migrate core 0003` after 0004 and 0005 have run. | Runs without error, but gives English labels instead of the original text, and erased regions and targeting restrictions do not return. | Document the reverse as lossy, or keep the originals as in A-200. |
| A-212 | Later | Confirmed | backend/services/admin_service.py:34 | `user.suspend()` | A crafted POST with action suspend for a DELETED account; the page hides the button. | A deleted account becomes SUSPENDED. Admin only. F-21. | Check the current status in the service. |
| A-213 | Later | Confirmed | backend/services/admin_service.py:119 | `if admin_user.user_id == user_id:` | A caller passing a string id. Web casts to int (apps/admin_panel/views.py:51) and no admin API exists, so this is latent today. | Self-suspension guard would be skipped. F-22. | Compare after converting to int. |
| A-214 | Later | Confirmed | backend/services/question_service.py:49 | `question_type=question_type,` | A caller other than the web form, which restricts choices (apps/surveys/forms.py:29). Latent today. | An unknown type is stored and submission later fails. F-24. | Validate the type in the service. |
| A-215 | Later | Confirmed | backend/services/question_service.py:247 | `if not options:` | Creating a multiple-choice question with one option. | Accepted now, then rejected only at publish. F-25. | Apply the two-option rule when creating. |
| A-216 | Later | Confirmed | backend/services/admin_service.py:90 | `"total_responses": self.response_repository.total_responses(),` | Admin report with a date range. | Total responses ignores the range while the charts use it, and total_users (:88) includes deleted accounts. F-28. | Apply the range and exclude deleted accounts, or label the totals as all-time. |
| A-217 | Later | Confirmed | backend/apps/core/models/respondent_profile.py:106 | `and self.interests` | Any survey targeting. | Interests are mandatory for eligibility, yet no targeting rule reads them (targeting_service.py:129 to 143), so they only ever exclude people. K-04. | Use interests in targeting, or stop requiring them for eligibility. |
| A-218 | Later | Confirmed | backend/repositories/survey_repository.py:52 | `status=SurveyStatus.PUBLISHED,` | A provider is suspended or soft-deleted while a survey is published. | Respondents can still see and answer that provider's survey, as neither the query nor ensure_can_answer checks the provider. | Decide the rule and enforce it in the service. |
| A-219 | Later | Question | backend/repositories/survey_repository.py:74 | `return Survey.objects.filter(survey_id=survey_id).delete()` | Provider deletes a CLOSED survey that has responses (allowed by apps/core/models/survey.py:63). | All responses, answers and sentiment results are removed for good, and the entry leaves each respondent's answered list. Team must confirm this is intended. | Use a soft delete, or refuse when responses exist. |
| A-220 | Later | Likely | backend/repositories/survey_repository.py:21 | `return Survey.objects.filter(provider_id=provider_id)` | Provider survey list after surveys are updated; same for user_repository.py:43. | No ordering in the query or model Meta, so PostgreSQL may change row order between page loads. | Add an explicit order. |
| A-221 | Later | Confirmed | planning/BACKEND_AUDIT.md:187 | `\| F-01 / K-01 \| 3ae3e46 \|` | Following any hash in the fix log (lines 187 to 200). | None of the 13 hashes is an ancestor of b77dbb3; the work landed squashed as 5abef48, so the document's evidence cannot be followed on develop. | Point the fix log at the commits on develop. |

**Counts by severity:** Blocker 3, Should 7, Later 12, Scope 0 (total 22).


---

# Part 7 — Defence material

All file:line references are at b77dbb3. Commit authorship is from `git log --author` on 1356167..b77dbb3, merge commits skipped.

Coverage note: Amer Khorsheed has three commits in the range (a8c1bb2 "complete 4-phase production remediation and hardening", 7295189, 5abf83f). The task names three members, so that work has no question set here. Someone on the team must be ready to explain it, because it includes the Celery wiring and the production settings block (backend/config/settings.py:185-195, 206-215).

## (a) Five questions on TASK-16 Part 1 (PR #56)

**Q1. Why three migrations for one feature instead of one?**
Each step does one kind of work. 0003 only adds columns (backend/apps/core/migrations/0003_profile_optional_fields.py:1 "schema only, no row updates in this transaction"). 0004 only updates rows (0004_map_profile_lists.py:1). 0005 only changes the schema again: it drops the old text column, renames the mapped column and narrows the regions (0005_profile_lists_final.py:48-81). Keeping row updates and table changes in separate transactions avoids PostgreSQL refusing an ALTER on a table with pending row events, and it makes each step reversible on its own.

**Q2. What happens to an old free-text value that matches no list entry?**
A profile region that cannot be mapped becomes "" and is counted in a printed summary (0004_map_profile_lists.py:135-138, 150-153). That profile is then incomplete, so it matches no survey until the respondent picks a governorate (backend/apps/core/models/respondent_profile.py:105, backend/services/targeting_service.py:55). A targeting region that cannot be mapped becomes NULL (0004:144-147), and NULL means "no region restriction" (targeting_service.py:141), so that survey widens to every region. Unknown interest words are dropped (0004:119-126). The team should say this openly: the mapping favours keeping the row, and the summary line is the only record of what was lost.

**Q3. How is completion_percent calculated, and what is the lowest value after registration?**
Seven details count equally: age, gender, region, interests, education, occupation, marital status (respondent_profile.py:21-29). The result is round(filled × 100 / 7) (respondent_profile.py:109-112). "Prefer not to say" is a non-empty code, so it counts as filled. Registration takes only the four required details (backend/services/authentication_service.py:66-72), so a new account starts at 57%.

**Q4. Validation appears in the serializer and in the service. Is that duplication?**
They do different jobs. The serializer checks the shape of the JSON and gives per-field errors (backend/apps/api/serializers.py:31-53). The service holds the business rule and is the only rule set that every entry point shares, including the web forms: `validate_profile_data` (backend/services/profile_service.py:76-112), which registration also calls before anything is saved (authentication_service.py:45-47). If the API layer were removed, the rule would still hold.

**Q5. Why is GET /profile/options/ public and unthrottled, and where do the lists come from?**
The register screen needs the lists before the user has a token, so the view extends PublicAPIView (backend/apps/api/views.py:183-193). It has no throttle_scope, and ScopedRateThrottle does not limit a view without a scope (views.py:184). It returns fixed data and takes no input. The lists have one source, the enums in backend/core/enums.py:44-114, read through `ProfileService.options` (profile_service.py:66-74). The migrations deliberately hold their own frozen copies (0004:2-3), so a later enum change cannot alter what an old migration does.

## (b) Six questions per member

### Yaman Almatar (c762367, 648396e, 7f00596, c40a293, 1f4d286)

**Q1. How are the four auth endpoints throttled, and what does an endpoint with no scope get?**
ScopedRateThrottle is the default class and the four rates are in settings (backend/config/settings.py:126-132). Each view names its scope (backend/apps/api/views.py:49, 76, 98, 125). A view without throttle_scope is not limited (views.py:184).

**Q2. Do the throttle counters work with several server processes?**
Only with Redis. REDIS_URL switches the cache to Redis (settings.py:140-147). Without it Django's default in-process cache is used, so each process counts separately. The demo uses one runserver process, so the limits hold there. planning/API.md:171 documents this.

**Q3. Can a client escape the limit by sending a fake X-Forwarded-For header?**
No. NUM_PROXIES defaults to 0 (settings.py:133), and with 0 DRF identifies the client by REMOTE_ADDR and ignores the header. If a proxy is added, NUM_PROXIES must be set to the number of proxies (planning/API.md:174-176).

**Q4. Why are there two compose files?**
docker-compose.yml is the demo database. docker-compose.prod.yml is an optional stack with its own project name and its own volume (docker-compose.prod.yml:2, 19, 52), so it cannot touch the demo data. Only the web container runs migrations (docker-compose.prod.yml:37, 45).

**Q5. How did PR #56 change region targeting, which used to compare free text (K-03)?**
Both sides now hold a governorate code. The criteria must be a Governorate value (backend/services/targeting_service.py:118-119), the profile must be one too (backend/services/profile_service.py:96-97), and the match is plain equality (targeting_service.py:141). Equality is now correct because the values come from one fixed list.

**Q6. Why upgrade to Django 5.2 during the project, and why pin Flutter in CI?**
Django 4.2 left extended support on 2026-04-07, and 5.2 is the current LTS (backend/requirements.txt:1; PR #55 body). pytest-django had to move to 4.11.0 because that is the first release that declares Django 5.2 (requirements.txt:5). Flutter CI is pinned to the laptop's version so CI and local runs cannot disagree (.github/workflows/flutter-ci.yml:36).

### Yousef Alzoubi (c68f73f, c47d461, 607910e, 1f0f388, b77dbb3)

**Q1. What happens at logout if the server cannot be reached?**
The app still signs out. The revoke call is best effort: an ApiException is swallowed and the `finally` block always clears both tokens (frontend/lib/features/auth/auth_repository.dart:83-98). The cost is that the refresh token stays valid on the server until it expires.

**Q2. Several requests get a 401 at the same moment. How many refresh calls are made?**
One. `_refreshing` holds the running refresh and the others wait on it (frontend/lib/core/api/api_client.dart:25-26, 73). A call whose rejected token has already been replaced does not refresh again (api_client.dart:69-72). This matters because rotation blacklists the old refresh token, so a second refresh with it would fail and sign the user out.

**Q3. How does the app handle refresh token rotation?**
After a refresh it stores the new access token and, when present, the new refresh token (api_client.dart:95-98). If the refresh is refused with 400 or 401 it clears the tokens and throws SessionExpiredException (api_client.dart:87-90).

**Q4. The respondent changes questions quickly. How do you stop draft saves overlapping?**
At most one save runs at a time. Each save point stores the newest answers in `_queued`, and the running loop picks them up when it finishes; identical answers are skipped (frontend/lib/features/answer/survey_answer_screen.dart:94-97, 99-108). So the last answers always win and requests cannot arrive out of order.

**Q5. Why is the submit timeout 60 seconds, and what happens if it times out but the server stored the response?**
Sentiment analysis can run inside the request (K-02), so submit gets a longer timeout than the default 15 seconds (frontend/lib/features/answer/answer_repository.dart:9-10; api_client.dart:19). After a network failure the app remembers it (survey_answer_screen.dart:215). If the retry then gets duplicate_response, the app treats the first send as successful and shows the sent screen (survey_answer_screen.dart:210-214).

**Q6. Is the profile percentage calculated in the app? What does the ring in the answer flow show?**
The percentage is not calculated in the app: it is read from the server's completion_percent (frontend/lib/features/profile/profile_models.dart:67, profile_hero.dart:55). The ring in the answer flow shows position, not completion: value = position × 100 / total, labelled "position/total" (survey_answer_screen.dart:369-373). That is decision D-118.

### Hasan Yahya (HoLqKoO) (920d0ec, f46cc05, db52069, b3d9928)

**Q1. Two submits pass the duplicate check at the same time. What stops two responses?**
The database constraint unique_response_per_survey_respondent (backend/apps/core/models/response.py:29). The second insert raises IntegrityError, the atomic block rolls back, and the service converts that to DuplicateResponse, which the API returns as 409 (backend/services/response_service.py:85-118; backend/apps/api/exceptions.py:20). Test: test_parallel_submits_store_one_response (backend/tests/services/test_response_service.py:616) and test_parallel_duplicate_submit_returns_409 (backend/tests/api/test_responses.py:243).

**Q2. Why check the constraint name in the error text? Why not catch every IntegrityError?**
Because a different integrity failure, such as a broken foreign key, is not a duplicate and must not be reported as one (response_service.py:115-119). Test: test_other_integrity_error_is_not_turned_into_duplicate_response (test_response_service.py:645). The weakness is that it depends on the constraint name appearing in the database message.

**Q3. Why is a draft one JSON field and not Answer rows?**
A draft has different rules: no question is required and every save replaces the whole list (backend/services/response_service.py:132-151). Storing it as JSON (backend/apps/core/models/response_draft.py:19) keeps half-finished data out of the Answer table, which the analytics read. The answers are still validated per question type before they are stored (response_service.py:141-145).

**Q4. Two first saves of a draft arrive together. What happens?**
Both may find no draft. The constraint unique_draft_per_survey_respondent (response_draft.py:25-30) lets one insert win. The other catches that IntegrityError, loads the winner's row and saves its own answers over it (response_service.py:153-163). Test: test_parallel_first_save_updates_the_existing_draft (test_response_service.py:770).

**Q5. Why does every draft call answer 409 after the survey has been submitted?**
All three draft calls and the submit call begin with the same `ensure_can_answer` check: respondent, survey exists, published, eligible, not already answered (response_service.py:51-72, 125, 134, 167). So the access rules cannot differ between paths, and the order of the checks gives the error order documented in planning/API.md:126.

**Q6. What did the health service change, and why does sentiment analysis run after commit?**
The readiness view used to reach the database itself. It now calls HealthService, and that service logs the failure and returns only True or False, so details never reach the client (backend/apps/core/views_health.py:22-24; backend/services/health_service.py:15-22). Sentiment analysis is registered with transaction.on_commit and robust=True (response_service.py:108-114), so an AI failure cannot undo a stored response.

## (c) Five hardest questions on the findings

To be completed after verification.


---

