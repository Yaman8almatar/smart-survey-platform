# Sequence diagram: UC-02 Manage demographic profile (FR-02)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: frontend/lib/features/profile/profile_screen.dart, frontend/lib/features/profile/profile_repository.dart,
  backend/apps/api/urls.py, backend/apps/api/views.py (ProfileOptionsView, ProfileView), backend/apps/api/serializers.py
  (ProfileSerializer), backend/apps/api/exceptions.py, backend/services/profile_service.py,
  backend/repositories/profile_repository.py, backend/apps/core/models/respondent_profile.py
Date / version: 2026-11-13, develop commit d3d2db2
```

The respondent opens the profile, the app loads the fixed lists and the stored profile in parallel, and Save sends the
whole profile with PUT (full replace). Every request carries the access token except the public options request.

```mermaid
sequenceDiagram
    actor R as Respondent
    participant S as ProfileScreen (Flutter screen)
    participant AR as ProfileRepository (app repository)
    participant V as ProfileOptionsView, ProfileView (API view, Presentation)
    participant PS as ProfileService (service, Business)
    participant DR as ProfileRepository (repository, Data Source)
    participant DB as PostgreSQL

    R->>S: Open the profile
    par Fixed lists
        S->>AR: options()
        AR->>V: GET /api/v1/profile/options/ (no token)
        V->>PS: options()
        PS-->>V: five code and label lists from core/enums.py (no database read)
        V-->>AR: 200 governorates, education, occupation, marital_status, interests
        AR-->>S: ProfileOptions
    and Stored profile
        S->>AR: load()
        AR->>V: GET /api/v1/me/profile/
        V->>PS: get_profile(user)
        PS->>PS: _ensure_respondent(user)
        PS->>DR: find_by_user_id(user_id)
        DR->>DB: SELECT FROM respondent_profiles WHERE user_id
        DB-->>DR: row or no row
        DR-->>PS: profile or None
        PS-->>V: profile or None
        alt Profile exists
            V-->>AR: 200 profile with completion_percent
            AR-->>S: Profile
        else No profile yet
            V-->>AR: 404 not_found
            AR-->>S: null
        end
    end
    S-->>R: Form with the stored values (or empty) and the completion percent

    R->>S: Change fields and tap Save
    S->>AR: save(profile)
    AR->>V: PUT /api/v1/me/profile/ age, gender, region, interests, education, occupation, marital_status
    V->>V: ProfileSerializer.is_valid (an omitted optional field becomes "")
    alt Field error in the request
        V-->>AR: 400 validation_error with fields (field name and messages)
        AR-->>S: ApiException with fields
        S-->>R: Highlight the fields, scroll to the first one
    else Request is valid
        V->>PS: update_profile(user, age, gender, region, interests, education, occupation, marital_status)
        PS->>PS: _ensure_respondent(user), validate_profile_data(...)
        alt Business rule broken
            PS-->>V: raise ValidationError
            V-->>AR: 400 validation_error (message, no fields)
            AR-->>S: ApiException
            S-->>R: Not saved, with the message and Try again
        else Rules pass
            PS->>DR: find_by_user_id(user_id)
            DR->>DB: SELECT FROM respondent_profiles WHERE user_id
            DB-->>DR: row or no row
            PS->>PS: profile.update_profile(...) replaces every value
            alt Profile exists
                PS->>DR: update(profile)
                DR->>DB: UPDATE respondent_profiles
            else First profile
                PS->>DR: save(profile)
                DR->>DB: INSERT INTO respondent_profiles
            end
            DB-->>DR: stored row
            DR-->>PS: profile
            PS-->>V: profile
            V-->>AR: 200 profile with the new completion_percent
            AR-->>S: Profile
            S-->>R: Profile saved, new completion percent
        end
    end
```

Full replace: the view passes `""` for an omitted optional field, so PUT clears education, occupation or marital
status when the app leaves them out. A user who is not a respondent gets 403 `unauthorized_action` from
`_ensure_respondent`; the app has only respondent accounts, so that path is not drawn.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person using the app. |
| Box at the top | Lifeline: one object or group of classes; the label names the class and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `par` / `and` frame | The parts run at the same time (`Future.wait` in the app). |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition in brackets. |
| `400`, `404`, `200` | HTTP status code; the word after it is the `error.code` of the shared error body. |
