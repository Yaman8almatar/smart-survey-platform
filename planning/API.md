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
4. On 401, call `POST /auth/token/refresh/` with `{"refresh": "..."}` to get a new `access`. If that fails, log in again.

Only respondents may use the API. Other roles can obtain a token but get 403 `permission_denied` on every endpoint except register and token. Token lifetimes are `API_ACCESS_TOKEN_LIFETIME` and `API_REFRESH_TOKEN_LIFETIME` in `config/settings.py`.

## Endpoints
| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/register/` | none | 201 `{id,email,name,role}` | 400 |
| POST | `/auth/token/` | none | 200 `{access,refresh}` | 400, 401 |
| POST | `/auth/token/refresh/` | none | 200 `{access}` | 400, 401 |
| GET | `/me/` | respondent | 200 `{id,email,name,role}` | 401, 403 |
| GET | `/me/profile/` | respondent | 200 `{age,gender,region,interests}` | 401, 403, 404 |
| PUT | `/me/profile/` | respondent | 200 profile | 400, 401, 403 |
| GET | `/surveys/eligible/` | respondent | 200 `[{id,title,description,question_count}]` | 401, 403 |
| GET | `/surveys/{id}/` | respondent | 200 `{id,title,description,questions[]}` | 401, 403, 404, 409 |
| POST | `/surveys/{id}/responses/` | respondent | 201 `{id,survey_id,submitted_at}` | 400, 401, 403, 404, 409 |
| GET | `/me/responses/` | respondent | 200 `[{survey_id,title,description,submitted_at}]` | 401, 403 |

Register and profile bodies: `age` 1 to 120, `gender` `MALE` or `FEMALE`, `region`, `interests`. Register also takes `name`, `email`, `password`.

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

## Error shape
Every error, including 401 and 403, has one shape. `fields` appears only for input validation errors.
```json
{"error": {"code": "validation_error", "message": "Invalid input.", "fields": {"age": ["Ensure this value is less than or equal to 120."]}}}
```
| Status | Codes |
|---|---|
| 400 | `validation_error`, `parse_error` |
| 401 | `not_authenticated`, `authentication_failed`, `invalid_credentials` |
| 403 | `permission_denied` (wrong role), `unauthorized_action` (survey not eligible) |
| 404 | `survey_not_found`, `question_not_found`, `not_found` |
| 405 | `method_not_allowed` |
| 409 | `duplicate_response`, `not_editable` (survey is not published) |
| 500 | `internal_error` |

Mapping lives in one place: `backend/apps/api/exceptions.py`.

## Known limits
- No pagination.
- No login throttling yet; add DRF throttle classes before any public deployment.
- URLs that do not exist (or a non-numeric survey id) return Django's HTML 404, not the JSON error shape.
- Use a `SECRET_KEY` of at least 32 bytes: JWT signing reuses it, and shorter keys trigger a PyJWT warning.
- The eligible list runs one count query per survey (small lists).
- K-02: sentiment analysis still runs in the request after the commit, so a submit with open-text answers can take longer when the AI service is slow.
- F-27: two parallel submits of the same survey can raise a database error, returned as 500 `internal_error` instead of 409.
- F-26: emails are case sensitive.
- Passwords are not checked for strength (same as the web form).
- Accounts suspended before the F-18 fix keep `is_active=true`; login is still refused by the service, but an already issued refresh token for such an account is not.
- Swagger UI loads its JavaScript from a CDN, so `/api/v1/docs/` needs internet access.
