# Sequence diagram: UC-12 View analytics and one response (FR-05, FR-07, FR-09, FR-13)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source)
Source of truth: backend/apps/analysis/views.py (analytics_dashboard), backend/apps/analysis/response_views.py
  (response_detail, response_inclusion), backend/services/analysis_service.py (get_survey_results, _filter_groups,
  _filter_can_show, _sentiment_breakdown, _pool_by_label), backend/services/disclosure.py (results_open, pool_groups),
  backend/services/survey_access.py (ensure_survey_owner), backend/services/quality_service.py (evaluate_survey,
  set_response_inclusion), backend/services/response_review_service.py (get_response),
  backend/repositories/response_repository.py, backend/repositories/analysis_repository.py
Date / version: 2026-11-27, develop commit 59f1957
```

The provider opens the results of his survey. Under 5 submitted responses nothing is read but the count (P-20). From 5
on he sees the summaries of the included responses, the sentiment of open answers by group with small groups pooled
(FR-05, P-15), one optional filter (FR-13), and each response under a number, never under an id (FR-07, FR-09).

```mermaid
sequenceDiagram
    actor P as Provider
    participant V as analytics_dashboard and response views (web views, Presentation)
    participant AS as AnalysisService (service, Business)
    participant D as disclosure (module, Business)
    participant QS as QualityService (service, Business)
    participant RR as ResponseReviewService (service, Business)
    participant REP as Response and Analysis repositories (Data Source)
    participant DB as PostgreSQL

    P->>V: GET /analysis/surveys/{id}/?group_by=... or ?filter=dimension:key
    V->>AS: get_survey_results(user, survey_id, group_by, filter_key)
    AS->>AS: ensure_survey_owner(user, survey_id)
    AS->>REP: count submitted responses
    REP->>DB: SELECT COUNT responses
    DB-->>REP: n
    AS->>D: results_open(n)
    alt n below 5 (P-20)
        D-->>AS: false
        AS-->>V: locked, n, 5
        V-->>P: Locked card: results open at 5 responses
    else n is 5 or more
        D-->>AS: true
        AS->>REP: included responses, their answers, sentiment results, questions without attention checks
        REP->>DB: SELECT ... WHERE is_excluded false
        DB-->>REP: rows
        AS->>AS: _filter_groups(included responses)
        opt a filter is chosen (FR-13)
            AS->>AS: keep the group's responses, drop group_by
            AS->>AS: _filter_can_show per question (5 of the group answered, whole pooled rows)
        end
        opt group_by is chosen (FR-05, FR-13)
            AS->>D: pool_groups(counts by label) via _pool_by_label
            D-->>AS: groups of 5 or more, the rest pooled as Other groups (combined)
        end
        AS-->>V: summaries, sentiment counts and breakdowns, filter options, responses over time
        V->>QS: evaluate_survey(user, survey_id)
        QS-->>V: verdicts per response (flags, score, band), counts
        V-->>P: Charts, sentiment panel, comparison tables, quality panel
    end

    P->>V: GET /analysis/surveys/{id}/responses/{number}/
    V->>RR: get_response(user, survey_id, number)
    RR->>QS: evaluate_survey(user, survey_id)
    QS-->>RR: responses in number order (submitted_at, then id)
    alt locked, or number outside 1 to total
        RR-->>V: locked, or ResponseNotFound
        V-->>P: Locked card, or the list with an error
    else valid number and results open
        RR->>REP: the response's answers with options, its sentiment results
        REP->>DB: SELECT answers, sentiment_analysis_results
        RR-->>V: number, date, active time, verdict, answers, previous and next numbers
        V-->>P: One response: no name, email, id or time of day
    end

    P->>V: POST /analysis/surveys/{id}/responses/{number}/inclusion/ (exclude or include)
    V->>QS: set_response_inclusion(user, survey_id, number, excluded)
    QS->>QS: ensure_survey_owner, then a response without a score cannot be excluded
    QS->>REP: UPDATE responses SET is_excluded, excluded_at for that number
    QS-->>V: count changed
    V-->>P: 302 back to the response with the message
```

The provider never sees a respondent's name or email: the pages show demographic groups and numbers only (FR-09).
Excluding a response changes the charts and the export but not the response count, so it never locks the results
again (P-08). The sentiment labels come from the analysis worker (state-sentiment-result.md); a result still PENDING
or RUNNING counts as waiting.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the provider using the website. |
| Box at the top | Lifeline: one object or group of objects; the label names it and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value or HTTP response. |
| Arrow back to the same lifeline | Internal step of that object. |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition. |
| `opt` frame | Optional part: runs only when its condition holds. |
| `302` | HTTP redirect after a form post. |
