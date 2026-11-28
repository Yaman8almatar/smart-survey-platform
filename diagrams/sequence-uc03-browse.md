# Sequence diagram: UC-03 Browse matching surveys (FR-01, FR-03, FR-08, FR-11)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: frontend/lib/features/surveys/eligible_surveys_screen.dart, frontend/lib/features/surveys/
  surveys_repository.dart, backend/apps/api/views.py (EligibleSurveysView), backend/services/survey_service.py
  (get_eligible_survey_items), backend/services/expected_time.py (expected_minutes),
  backend/repositories/survey_repository.py (find_eligible_for_respondent), backend/repositories/profile_repository.py,
  backend/repositories/quality_repository.py (find_valid_active_ms_by_survey_ids)
Date / version: 2026-11-27, develop commit 59f1957
```

The respondent sees the published surveys that match his profile and are open today, ranked by the interests they
share with him, each with its question count, expected time and closing date. Search and the three chips filter the
list inside the app; they send no request.

```mermaid
sequenceDiagram
    actor R as Respondent
    participant S as EligibleSurveysScreen (Flutter screen)
    participant AR as SurveysRepository (app repository)
    participant V as EligibleSurveysView (API view, Presentation)
    participant SS as SurveyService (service, Business)
    participant REP as Profile, Survey and Quality repositories (Data Source)
    participant DB as PostgreSQL

    R->>S: Open the app after log-in (or pull to refresh)
    S->>AR: eligibleSurveys()
    AR->>V: GET /api/v1/surveys/eligible/
    V->>SS: get_eligible_survey_items(user)
    SS->>SS: _ensure_respondent(user)
    SS->>REP: profile of the user
    REP->>DB: SELECT respondent_profiles
    alt no profile, or profile not complete
        SS-->>V: empty list
    else complete profile
        SS->>REP: find_eligible_for_respondent(profile, user_id)
        REP->>DB: SELECT published surveys with criteria matching the profile, open today by opens_on and closes_on, not answered by the user, with question counts, newest first
        DB-->>REP: surveys
        SS->>REP: find_valid_active_ms_by_survey_ids(ids)
        REP->>DB: SELECT active times of valid responses
        DB-->>REP: times per survey
        SS->>SS: sort by shared interests, most first (stable, so newest first among equals)
        SS->>SS: expected_minutes: median active time from 20 valid responses, else seconds per question type
        SS-->>V: survey, question_count, expected_minutes, published_on, closes_on per item
    end
    V-->>AR: 200 list in that order
    AR-->>S: List of EligibleSurvey
    S-->>R: Cards: title, N questions, About N min, Closes date

    loop while the respondent types or taps a chip
        R->>S: Search text, or All, Under 5 min, New this week
        S->>S: keep the cards whose title or description contains the text and that pass the chip, in the server's order
        S-->>R: Filtered cards, no request
    end
```

A paused survey, a survey before its opening date and a survey after its closing date are not in the list, because the
query keeps PUBLISHED surveys that are open today (state-survey-lifecycle.md). The matching rule is the same as the
reach count of UC-10; a parity test keeps the forms equal (P-18).

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person using the app. |
| Box at the top | Lifeline: one object or group of objects; the label names it and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `loop` frame | Repeated while the condition holds. |
| `200` | HTTP status code. |
