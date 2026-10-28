---
name: api-endpoint
description: Use when adding or changing a REST endpoint under /api/v1/ for the respondent Flutter app, or when a task says "add endpoint", "expose service X over the API", or edits backend/apps/api/.
---

# Add a REST endpoint for the respondent app

API views are thin: validate input, call an EXISTING service, map the result to JSON.
Dependency direction: API view -> service -> repository -> model. No ORM calls in `apps/api/`.

## Steps (in this order)
CLAUDE.md still applies (Plan Mode first, `/handoff` last).

1. Read `planning/API.md` (paths, error codes, known limits). Find the service method that already does the work.
   None fits? The missing rule goes into the service first (step 2).
2. Service gap only: add a failing test to the matching file in `backend/tests/services/`, then the rule in
   `backend/services/`. Never put a business rule, ownership check or role check in the view or serializer.
3. **API test next, before the view**, in `backend/tests/api/` (fixtures `client`, `authenticate`, `respondent`,
   `survey`, `make_survey` in `conftest.py`; extend the matching `test_*.py`).
   Cover: success, 401 without token, 403 for provider and admin, every error case the service can raise.
   Add the route to `PROTECTED_ENDPOINTS` in `tests/api/test_access.py`. Run it and watch it fail.
4. Implement:
   - `serializers.py`: shape and type-check only (plain `Serializer`, not business rules).
   - `views.py`: `APIView`, one service call, `Response(...)`. Default permission is `IsRespondent`;
     only register/token use `PublicAPIView`.
   - `urls.py`: add the path; ids are `<int:...>`.
5. Errors: raise `core.exceptions` from the service and let `apps/api/exceptions.py` map them.
   New exception class -> add it to `CORE_ERRORS` and a case in `tests/api/test_foundation.py`.
   Never build error JSON in a view.
6. Swagger: `@extend_schema(tags=..., request=..., responses={200: X, 4xx: ErrorSerializer}, summary=...)`.
   Write endpoints also get `OpenApiExample` request and response examples (see `SubmitResponseView`).
7. Update `planning/API.md`: endpoint table row, body fields, any new error code.
8. Verify from `backend/` with the repo venv (`.venv` at the repository root):
   ```
   python manage.py check
   python -m pytest tests -q
   python manage.py spectacular --file schema.yml --validate
   ```
   Delete `schema.yml` afterwards; never commit it.

## Quick reference
| Need | Where |
|---|---|
| Exception to HTTP status/code | `apps/api/exceptions.py` `CORE_ERRORS` |
| Role gate | `apps/api/permissions.py` `IsRespondent` |
| Token lifetimes, CORS | `config/settings.py` |

## Common mistakes
- Calling `Model.objects` or a repository from a view: go through the service.
- Coercing types in the serializer so the service never sees the bad value: keep service validation authoritative.
- Forgetting the 401/403 rows in `test_access.py`.
- Reusing a path that already exists (`me/responses/` is the history list): check `apps/api/urls.py` first.
- Committing `schema.yml`.
