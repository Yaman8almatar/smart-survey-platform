# Sequence diagram: UC-06 View answered surveys (FR-01)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: frontend/lib/features/surveys/answered_surveys_screen.dart, frontend/lib/features/surveys/surveys_repository.dart,
  backend/apps/api/urls.py, backend/apps/api/views.py (AnsweredSurveysView), backend/apps/api/serializers.py
  (AnsweredSurveySerializer), backend/services/response_service.py (get_answered_surveys),
  backend/repositories/response_repository.py (find_by_respondent_id)
Date / version: 2026-11-13, develop commit d3d2db2
```

The respondent opens the list of surveys already sent. The server returns them newest first; the app keeps that order.
The list is read-only: an answered survey cannot be sent again.

```mermaid
sequenceDiagram
    actor R as Respondent
    participant S as AnsweredSurveysScreen (Flutter screen)
    participant AR as SurveysRepository (app repository)
    participant V as AnsweredSurveysView (API view, Presentation)
    participant RS as ResponseService (service, Business)
    participant DR as ResponseRepository (repository, Data Source)
    participant DB as PostgreSQL

    R->>S: Open answered surveys (or pull to refresh)
    S->>AR: answeredSurveys()
    AR->>V: GET /api/v1/me/responses/
    V->>RS: get_answered_surveys(user)
    RS->>RS: _ensure_respondent_for_answered_surveys(user)
    RS->>DR: find_by_respondent_id(user_id)
    DR->>DB: SELECT responses JOIN surveys WHERE respondent_id ORDER BY submitted_at DESC
    DB-->>DR: rows, newest first
    DR-->>RS: responses with their survey
    RS-->>V: survey_id, survey_title, survey_description, submitted_at per response
    V-->>AR: 200 list of survey_id, title, description, submitted_at
    AR-->>S: List of AnsweredSurvey in the server's order
    alt List is empty
        S-->>R: No answered surveys yet. Surveys you send appear here with the day you sent them.
    else One or more surveys
        S-->>R: One row per survey, newest first, with the day it was sent
    end
```

A user who is not a respondent gets 403 `unauthorized_action` from `_ensure_respondent_for_answered_surveys`; the app
has only respondent accounts, so that path is not drawn. The index `responses_resp_sub_idx`
(respondent_id, submitted_at) matches this query, see erd.md.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person using the app. |
| Box at the top | Lifeline: one object; the label names the class and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition in brackets. |
| `200` | HTTP status code. |
