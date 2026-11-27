# Sequence diagram: UC-13 Export results (FR-14)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: backend/apps/analysis/export_views.py (response_export_csv, response_export_xlsx,
  _export_table_or_redirect, export_table, _clean, _guard), backend/services/response_review_service.py
  (export_responses), backend/services/quality_service.py (evaluate_survey), backend/repositories/
  (question, response and analysis repositories)
Date / version: 2026-11-27, develop commit 59f1957
```

The provider downloads the included responses of his survey with their quality verdicts, as CSV or as an Excel
workbook. Each row carries the response's list number, never its id; excluded responses keep their numbers but give
no row. Text cells are cleaned so that a spreadsheet never runs them as formulas.

```mermaid
sequenceDiagram
    actor P as Provider
    participant V as response_export_csv or response_export_xlsx (web views, Presentation)
    participant RR as ResponseReviewService (service, Business)
    participant QS as QualityService (service, Business)
    participant REP as Question, Response and Analysis repositories (Data Source)
    participant DB as PostgreSQL

    P->>V: GET /analysis/surveys/{id}/responses/export/csv/ (or /xlsx/)
    V->>RR: export_responses(user, survey_id)
    RR->>QS: evaluate_survey(user, survey_id)
    QS->>QS: owner check, results_open (P-20), verdicts per response
    alt not the owner
        QS-->>RR: UnauthorizedAction or SurveyNotFound
        RR-->>V: error
        V-->>P: 302 to the provider dashboard with the message
    else fewer than 5 responses
        QS-->>RR: locked
        RR-->>V: locked
        V-->>P: 302 to the response list, which shows the locked card
    else results open
        QS-->>RR: responses in number order with flags, score, band, inclusion
        RR->>REP: questions with options, included answers, sentiment statuses
        REP->>DB: three SELECTs
        DB-->>REP: rows
        RR-->>V: questions and one row per included response
        V->>V: export_table: header, then one line per row
        V->>V: _clean each text cell: strip control characters, then _guard puts an apostrophe before a cell that starts with = + - @, a tab or a carriage return
        alt CSV
            V-->>P: 200 survey-{id}-responses.csv, UTF-8 with a byte-order mark
        else Excel
            V-->>P: 200 survey-{id}-responses.xlsx, one sheet "Responses" (openpyxl)
        end
    end
```

The order of `_clean` matters: the control characters are stripped first, because a cell such as a bell character
followed by "=1" would pass the guard and then become the formula "=1" once stripped (D-226 (3)).

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the provider using the website. |
| Box at the top | Lifeline: one object or group of objects; the label names it and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `200`, `302` | HTTP status codes. |
