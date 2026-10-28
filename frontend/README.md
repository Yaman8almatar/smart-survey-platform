# Smart Survey — respondent app (Flutter)

Respondents log in with email and password and see the surveys they are eligible for.
API contract: `planning/API.md`.

## Run against the local API
Run from the repository root, then each block in its own terminal.

```
docker compose up -d
```

```
cd backend
python manage.py seed_demo_data
python manage.py runserver
```

```
cd frontend
flutter pub get
flutter run -d chrome --web-port 5000
```

- Log in as `respondent@demo.com`. The password is printed by `seed_demo_data`.
- `provider@demo.com` is refused: the app is for respondents only.
- Keep `--web-port 5000`. The backend allows CORS only for `http://localhost:*` and
  `http://127.0.0.1:*`, and only when `DEBUG=True` in `backend/.env`.

## API base URL
The default is `http://127.0.0.1:8000/api/v1/` on web and `http://10.0.2.2:8000/api/v1/` on the
Android emulator. Override it at build or run time:

```
flutter run -d chrome --web-port 5000 --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1/
```

The URL is defined in one place: `lib/core/api/api_config.dart`.

## Checks
```
flutter analyze
flutter test
```

## Layout
- `lib/core/api/` — shared `ApiClient` (Bearer header, one refresh on 401), `TokenStore`, `ApiException`.
- `lib/features/<name>/` — screen, repository and models per feature (`auth`, `surveys`).
- `lib/theme/` — design tokens (`SsColors`, `SsSpace`, `SsRadius`, `SsLayout`) and the app theme.
