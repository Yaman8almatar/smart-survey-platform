# Sequence diagram: UC-14 Review survey, with the provider's submit from UC-11 (FR-12)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: backend/apps/surveys/views.py (submit_for_review), backend/apps/admin_panel/views.py (review_queue,
  review_survey, approve_survey, reject_survey), backend/services/survey_service.py (submit_for_review,
  get_publish_preview, _get_publishable_survey), backend/services/survey_review_service.py (list_pending, get_review,
  approve, reject, _ensure_pending), backend/repositories/survey_repository.py (find_pending_review,
  find_by_id_for_update, update), backend/repositories/profile_repository.py (count_matching),
  backend/apps/core/models/survey.py (submit_for_review, approve, reject)
Date / version: 2026-11-27, develop commit 59f1957
```

A provider submits a complete draft; it waits as PENDING_REVIEW until an admin approves it (it is published at once)
or rejects it with a reason (it goes back to DRAFT). The state changes are in state-survey-lifecycle.md.

```mermaid
sequenceDiagram
    actor P as Provider
    actor A as Admin
    participant W as Web views (surveys and admin_panel, Presentation)
    participant SS as SurveyService (service, Business)
    participant RV as SurveyReviewService (service, Business)
    participant SR as SurveyRepository (repository, Data Source)
    participant PR as ProfileRepository (repository, Data Source)
    participant DB as PostgreSQL

    P->>W: GET /surveys/{id}/submit/
    W->>SS: get_publish_preview(user, survey_id)
    SS->>SS: _get_publishable_survey: owner, DRAFT, dates, questions, options, attention answers, criteria
    SS-->>W: banded reach, criteria, question count
    W-->>P: Submit confirmation with the reach
    P->>W: POST /surveys/{id}/submit/
    W->>SS: submit_for_review(user, survey_id)
    SS->>SS: _get_publishable_survey (the same checks again)
    SS->>SR: update(survey after submit_for_review())
    SR->>DB: UPDATE surveys SET status PENDING_REVIEW, submitted_at, review fields cleared
    SS-->>W: survey
    W-->>P: 302 to the list with "Survey submitted for review."

    A->>W: GET /admin-panel/reviews/
    W->>RV: list_pending(admin)
    RV->>SR: find_pending_review()
    SR->>DB: SELECT surveys WHERE status PENDING_REVIEW ORDER BY submitted_at
    RV-->>W: rows, oldest first
    W-->>A: Review queue
    A->>W: GET /admin-panel/reviews/{id}/
    W->>RV: get_review(admin, survey_id)
    RV-->>W: survey, provider, criteria, banded reach, questions
    W-->>A: Review page

    alt Approve
        A->>W: POST /admin-panel/reviews/{id}/approve/
        W->>RV: approve(admin, survey_id)
        RV->>RV: _ensure_admin
        RV->>SR: find_by_id_for_update(survey_id) inside a transaction
        SR->>DB: SELECT ... FOR UPDATE
        DB-->>SR: survey row, locked
        RV->>RV: _ensure_pending, then closing date not passed
        RV->>PR: count_matching(criteria)
        PR->>DB: SELECT COUNT matching profiles
        DB-->>PR: count
        RV->>SR: update(survey after approve(admin): reach_at_publish, reviewed_by, reviewed_at, PUBLISHED, published_at)
        SR->>DB: UPDATE surveys, then COMMIT
        W-->>A: 302 to the queue with "Survey approved and published."
    else Reject
        A->>W: POST /admin-panel/reviews/{id}/reject/ with reason
        W->>RV: reject(admin, survey_id, reason)
        RV->>RV: _ensure_admin, then reason of 1 to 1000 characters
        alt reason missing or too long
            RV-->>W: ValidationError
            W-->>A: 302 back to the review page with the message
        else reason valid
            RV->>SR: find_by_id_for_update(survey_id) inside a transaction
            RV->>RV: _ensure_pending
            RV->>SR: update(survey after reject(admin, reason): DRAFT, rejection_reason, reviewed_by, reviewed_at)
            SR->>DB: UPDATE surveys, then COMMIT
            W-->>A: 302 to the queue with "Survey returned to the provider."
        end
    end
```

The row lock makes a second admin who decides on the same survey at the same moment wait; he then finds it no longer
pending and gets "This survey is no longer waiting for review." The reach stored at approval is unbanded on purpose:
every display of it goes through `disclosure.band`.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: a person using the website (provider or admin). |
| Box at the top | Lifeline: one object; the label names the class and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `302` | HTTP redirect after a form post. |
