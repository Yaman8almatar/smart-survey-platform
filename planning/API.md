# Respondent REST API (v1)

Everything a respondent can do on the web today, for the Flutter client. JSON only. No pagination yet (lists are small; later item).

## Base URL
| Client | Base URL |
|---|---|
| Flutter on Chrome (web dev server) | `http://127.0.0.1:8000/api/v1/` |
| Flutter on the Android emulator | `http://10.0.2.2:8000/api/v1/` |
| Swagger UI | `/api/v1/docs/` |
| OpenAPI schema | `/api/v1/schema/` |

Android emulator notes:
- `10.0.2.2` is the emulator's alias for the host machine's `127.0.0.1`. `127.0.0.1` inside the emulator points at the emulator itself.
- Start the server with `python manage.py runserver 0.0.0.0:8000`.
- Add `10.0.2.2` to `ALLOWED_HOSTS` in `backend/.env` (comma separated), or Django answers 400 `DisallowedHost`.
- Plain `http` needs `android:usesCleartextTraffic="true"` in the debug manifest.
- CORS does not apply to the Android app. For Chrome, CORS allows only `http://localhost:*` and `http://127.0.0.1:*`, and only when `DEBUG=True`.

## Auth flow
1. `POST /auth/register/` creates the respondent and the profile. It returns 201 and **no tokens**.
2. `POST /auth/token/` with `email` and `password` returns `access` (30 minutes) and `refresh` (7 days). Suspended or deleted accounts get 401 `invalid_credentials`.
3. Send `Authorization: Bearer <access>` on every other call.
4. On 401, call `POST /auth/token/refresh/` with `{"refresh": "..."}`. It returns a new `access` and a new `refresh`
   (rotation): store both, because the old refresh token is blacklisted and refused from then on. If refresh fails, log in again.
5. On logout, call `POST /auth/logout/` with `{"refresh": "..."}`. It returns 204 and blacklists that refresh token, so it
   can no longer be used, even if a copy was kept. The access token stays valid until it expires (30 minutes).
   The call needs no `Authorization` header. The Flutter client (`AuthRepository.logout`) sends it without one, treats
   revocation as best effort, and always deletes both stored tokens, even on a 400, a network failure or when no refresh
   token is stored (then it sends no request).

Only respondents may use the API. Other roles can obtain a token but get 403 `permission_denied` on every endpoint except register, token and `GET /profile/options/`. Token lifetimes are `API_ACCESS_TOKEN_LIFETIME` and `API_REFRESH_TOKEN_LIFETIME` in `config/settings.py`.

## Endpoints
| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/register/` | none | 201 `{id,email,name,role}` | 400, 429 |
| POST | `/auth/token/` | none | 200 `{access,refresh}` | 400, 401, 429 |
| POST | `/auth/token/refresh/` | none | 200 `{access,refresh}` | 400, 401, 429 |
| POST | `/auth/logout/` | none | 204 | 400, 429 |
| GET | `/me/` | respondent | 200 `{id,email,name,role}` | 401, 403 |
| GET | `/me/profile/` | respondent | 200 `{age,gender,region,interests,education,occupation,marital_status,completion_percent}` | 401, 403, 404 |
| PUT | `/me/profile/` | respondent | 200 profile | 400, 401, 403 |
| GET | `/profile/options/` | none | 200 `{governorates,education,occupation,marital_status,interests}` | — |
| GET | `/surveys/eligible/` | respondent | 200 `[{id,title,description,question_count}]` | 401, 403 |
| GET | `/surveys/{id}/` | respondent | 200 `{id,title,description,questions[]}` | 401, 403, 404, 409 |
| POST | `/surveys/{id}/responses/` | respondent | 201 `{id,survey_id,submitted_at}` | 400, 401, 403, 404, 409 |
| GET | `/surveys/{id}/draft/` | respondent | 200 `{survey_id,answers,started_at,updated_at}` | 401, 403, 404, 409 |
| PUT | `/surveys/{id}/draft/` | respondent | 200 draft | 400, 401, 403, 404, 409 |
| DELETE | `/surveys/{id}/draft/` | respondent | 204 | 401, 403, 404, 409 |
| GET | `/me/responses/` | respondent | 200 `[{survey_id,title,description,submitted_at}]` | 401, 403 |

Register and profile bodies (FR-02, D-108): `age` 1 to 120, `gender` `MALE` or `FEMALE`, `region` one governorate code,
`interests` a list of 1 to 12 distinct interest codes. Register also takes `name`, `email`, `password`; it does not take
the optional fields (they start as `""`).
```json
{"age": 28, "gender": "FEMALE", "region": "DAMASCUS", "interests": ["TECHNOLOGY", "CAREERS"],
 "education": "BACHELOR", "occupation": "", "marital_status": "PREFER_NOT_TO_SAY"}
```
- The profile also has three optional fields: `education`, `occupation`, `marital_status`. Each is `""` (not answered)
  or one code of its list.
- `PUT /me/profile/` is a **full replace**: send all seven fields. An optional field that is left out is stored as `""`.
- `completion_percent` is read-only (GET and PUT responses). Seven details count equally: age, gender, region, interests
  (at least one), education, occupation, marital status; `PREFER_NOT_TO_SAY` counts as filled.
  Percent = round(filled × 100 / 7): 0, 14, 29, 43, 57, 71, 86, 100.
- The field keeps the name `region`; the UI calls it "Governorate". Targeting matches by code equality.
- Field errors name the field, for example `{"region": ["Choose a governorate from the list."]}` or
  `{"interests": ["Choose at least one interest."]}`.

`GET /profile/options/` needs no token and is not throttled. Each list is `[{"code", "label"}]` in display order:

| Key | Codes, in order |
|---|---|
| `governorates` | `ALEPPO`, `AL_HASAKAH`, `AS_SUWAYDA`, `DAMASCUS`, `DARAA`, `DEIR_EZ_ZOR`, `HAMA`, `HOMS`, `IDLIB`, `LATAKIA`, `QUNEITRA`, `RAQQA`, `RIF_DIMASHQ`, `TARTUS`, `OUTSIDE_SYRIA` |
| `education` | `BASIC`, `SECONDARY`, `INSTITUTE`, `BACHELOR`, `MASTER`, `DOCTORATE`, `PREFER_NOT_TO_SAY` |
| `occupation` | `STUDENT`, `PUBLIC_SECTOR`, `PRIVATE_SECTOR`, `SELF_EMPLOYED`, `LOOKING_FOR_WORK`, `HOMEMAKER`, `RETIRED`, `OTHER`, `PREFER_NOT_TO_SAY` |
| `marital_status` | `SINGLE`, `MARRIED`, `DIVORCED`, `WIDOWED`, `PREFER_NOT_TO_SAY` |
| `interests` | `TECHNOLOGY`, `EDUCATION`, `HEALTH`, `SPORTS`, `FOOD`, `TRAVEL`, `SHOPPING`, `FINANCE`, `CAREERS`, `ARTS`, `ENTERTAINMENT`, `ENVIRONMENT` |

Labels come from the API (`backend/core/enums.py`); clients show the label and send the code.

Question fields: `id`, `text`, `type` (`MULTIPLE_CHOICE`, `RATING_SCALE`, `OPEN_TEXT`), `is_required`, `order_index`, `options[{id,text}]`, `rating_values` (`[1,2,3,4,5]` for rating questions, else `[]`).

Submit body:
```json
{"answers": [
  {"question_id": 1, "selected_option_id": 2},
  {"question_id": 2, "rating_value": 4},
  {"question_id": 3, "answer_value": "Clear and quick."}
]}
```
Use `selected_option_id` for multiple choice, `rating_value` (1 to 5) for rating, `answer_value` for open text. Optional questions may be left out.

A successful submit deletes the draft; the response keeps the draft's started_at (not exposed in the API yet; for FR-18).

## Drafts (FR-06)
A respondent's unsent answers are kept per survey until the respondent submits them. Each respondent has at most one draft per survey.

| Call | Success | Meaning |
|---|---|---|
| `GET /surveys/{id}/draft/` | 200 draft | Load the saved draft. |
| `PUT /surveys/{id}/draft/` | 200 draft | Save. The first save creates the draft; later saves replace it. |
| `DELETE /surveys/{id}/draft/` | 204, no body | Delete the draft. Also 204 when there is none. |

`PUT` body, the same fields as submit:
```json
{"answers": [
  {"question_id": 1, "selected_option_id": 2},
  {"question_id": 3, "answer_value": "Clear so far."}
]}
```
- **Full replace:** the stored list becomes exactly the sent list. `{"answers": []}` is allowed and stores an empty list.
- No question is required, so a required question may be missing or empty. Every sent value follows the per-type rules of submit.

200 shape. `answers` holds `question_id` and only the fields that are not null. `started_at` is set by the first save and never changes; `updated_at` changes on every save.
```json
{"survey_id": 5,
 "answers": [
   {"question_id": 1, "selected_option_id": 2},
   {"question_id": 3, "answer_value": "Clear so far."}
 ],
 "started_at": "2026-11-08T09:30:00Z",
 "updated_at": "2026-11-08T09:34:00Z"}
```

Errors. The first five rows apply to all three calls and are checked in this order, so after a submit every call answers 409 `duplicate_response`.

| Status | Code | When |
|---|---|---|
| 403 | `permission_denied` | The token does not belong to a respondent. |
| 404 | `survey_not_found` | The survey does not exist. |
| 409 | `not_editable` | The survey is not published (for example, it is closed). |
| 403 | `unauthorized_action` | The respondent is not eligible for the survey. |
| 409 | `duplicate_response` | The respondent already submitted the survey. |
| 404 | `draft_not_found` | `GET` only: the respondent has no draft for the survey. |
| 400 | `validation_error` | `PUT` only: the body is malformed, a `question_id` is repeated, an `answer_value` is over 2000 characters, a rating is outside 1 to 5, an option belongs to another question, or a field does not fit the question type. |
| 404 | `question_not_found` | `PUT` only: a `question_id` does not belong to the survey. |
| 401 | `not_authenticated` | No token was sent (all three calls). |

## Error shape
Every error, including 401 and 403, has one shape. `fields` appears only for input validation errors.
```json
{"error": {"code": "validation_error", "message": "Invalid input.", "fields": {"age": ["Ensure this value is less than or equal to 120."]}}}
```
| Status | Codes |
|---|---|
| 400 | `validation_error`, `parse_error`, `invalid_token` (logout) |
| 401 | `not_authenticated`, `authentication_failed`, `invalid_credentials` |
| 403 | `permission_denied` (wrong role), `unauthorized_action` (survey not eligible) |
| 404 | `survey_not_found`, `question_not_found`, `draft_not_found`, `not_found` |
| 405 | `method_not_allowed` |
| 409 | `duplicate_response`, `not_editable` (survey is not published) |
| 429 | `throttled` (too many auth requests; see Throttling) |
| 500 | `internal_error` |

Mapping lives in one place: `backend/apps/api/exceptions.py`.

## Throttling
The four auth endpoints are rate limited per client IP with DRF `ScopedRateThrottle`, one scope each. The rates live in
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` in `config/settings.py`:

| Endpoint | Scope | Rate |
|---|---|---|
| `POST /auth/token/` | `auth_token` | 10/min |
| `POST /auth/token/refresh/` | `auth_refresh` | 30/min |
| `POST /auth/register/` | `auth_register` | 5/min |
| `POST /auth/logout/` | `auth_logout` | 30/min |

A request over the limit gets 429 `throttled` and a `Retry-After` header (seconds to wait). Scopes are independent: using up
login does not block token refresh. Endpoints without a scope, including `/healthz/live/` and `/healthz/ready/`, are not
throttled; `GET /profile/options/` is not throttled either. The counters live in the Django cache; set `REDIS_URL` so that several server processes share them (without it
each process keeps its own in-memory counters).

The client is identified by the connection address (REMOTE_ADDR), so clients cannot change their identity with
X-Forwarded-For. Everyone behind one NAT gateway shares one limit. If a proxy is added in front of the API, set
NUM_PROXIES to the number of proxies.

Throttling limits abuse; it is not complete brute-force protection, because clients can change IP addresses.

## Known limits
- No pagination.
- URLs that do not exist (or a non-numeric survey id) return Django's HTML 404, not the JSON error shape.
- Use a `SECRET_KEY` of at least 32 bytes: JWT signing reuses it, and shorter keys trigger a PyJWT warning.
- The eligible list runs one count query per survey (small lists).
- K-02: sentiment analysis still runs in the request after the commit, so a submit with open-text answers can take longer when the AI service is slow.
- F-27: two parallel submits of the same survey can raise a database error, returned as 500 `internal_error` instead of 409.
- F-26: emails are case sensitive.
- Passwords are not checked for strength (same as the web form).
- Accounts suspended before the F-18 fix keep `is_active=true`; login is still refused by the service, but an already issued refresh token for such an account is not.
- Swagger UI loads its JavaScript from a CDN, so `/api/v1/docs/` needs internet access.
