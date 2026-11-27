# Sequence diagram: UC-10 Define targeting and preview reach (FR-03)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: backend/apps/surveys/views.py (targeting_criteria, targeting_reach), backend/static/js/site.js (W-03
  reach card), backend/services/targeting_service.py (reach, describe_reach, save_criteria, build_criteria),
  backend/services/disclosure.py (band), backend/repositories/profile_repository.py (count_pool, count_matching),
  backend/repositories/targeting_repository.py
Date / version: 2026-11-27, develop commit 59f1957
```

The provider chooses who may answer a draft survey and sees, while editing, how many respondents match. The count is
banded (P-19): 0 is shown as none, 1 to 4 as "fewer than 5" without a number, 5 and more as the number. Nothing is
saved until the provider presses Save.

```mermaid
sequenceDiagram
    actor P as Provider
    participant B as Browser (targeting page, site.js)
    participant V as targeting_criteria and targeting_reach (web views, Presentation)
    participant TS as TargetingService (service, Business)
    participant D as disclosure (module, Business)
    participant PR as ProfileRepository (repository, Data Source)
    participant TR as TargetingRepository (repository, Data Source)
    participant DB as PostgreSQL

    P->>B: Open Targeting for a draft survey
    B->>V: GET /surveys/{id}/targeting/
    V->>TS: get_criteria_initial(user, survey_id)
    TS->>TR: find_by_survey_id(survey_id)
    TR->>DB: SELECT survey_targeting_criteria
    DB-->>TR: row or none
    TR-->>TS: saved criteria or none
    TS-->>V: initial values
    V->>TS: reach(user, survey_id, initial values)
    Note over V,TS: the first reach is rendered in the page
    TS->>TS: _get_owned_draft_survey(user, survey_id)
    TS->>PR: count_pool()
    PR->>DB: SELECT COUNT active respondents with a complete profile
    DB-->>PR: total
    alt criteria open to everyone
        TS-->>V: state everyone, count = total, percent 100
    else narrowed
        TS->>PR: count_matching(criteria)
        PR->>DB: SELECT COUNT profiles matching gender, age and the five lists
        DB-->>PR: matching count
        TS->>D: band(count)
        D-->>TS: none (0), few (1 to 4, no number) or exact
        TS-->>V: state, count or none, total, percent
    end
    V-->>B: 200 page with the form and the reach card
    B-->>P: Form and the reach ring

    loop every change, 400 ms after the last one
        P->>B: Change a criterion
        B->>V: POST /surveys/{id}/targeting/reach/ (unsaved form values)
        alt form not valid
            V-->>B: 400 validation_error with the field
        else valid
            V->>TS: reach(user, survey_id, values)
            Note over TS,DB: same steps as above, nothing is saved
            TS-->>V: banded reach
            V-->>B: 200 JSON state, count, total, percent
        end
        B-->>P: Reach ring and sentence updated
    end

    P->>B: Save
    B->>V: POST /surveys/{id}/targeting/
    V->>TS: save_criteria(user, survey_id, values)
    TS->>TS: _get_owned_draft_survey, then build_criteria checks gender and that the minimum age is not above the maximum
    TS->>TR: create_or_update(survey, gender, ages, five lists)
    TR->>DB: INSERT or UPDATE survey_targeting_criteria
    DB-->>TR: ok
    TS-->>V: criteria
    V-->>B: 302 to the survey list with "Targeting criteria saved successfully."
    B-->>P: Survey list
```

Only the owner of a DRAFT survey reaches the count (`_get_owned_draft_survey`); any other survey gives an error
message on the page or an error code in the JSON. `count_matching` holds the same rule as
`TargetingService.profile_matches_criteria` and `SurveyRepository.find_eligible_for_respondent`; a parity test keeps
the three equal (P-18). The reach stored with the survey is counted again when an admin approves it (UC-14).

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person using the website. |
| Box at the top | Lifeline: one object; the label names the class or module and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `loop` frame | Repeated while the condition holds. |
| Note | Comment on the lifelines it spans. |
| `200`, `302`, `400` | HTTP status codes. |
