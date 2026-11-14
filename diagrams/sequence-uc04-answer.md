# Sequence diagram: UC-04 Answer a survey, with draft and resume (FR-06)

```
Basis: team convention; diagrams/README.md (layers Presentation / Business / Data Source); planning/API.md (known limit K-02)
Source of truth: frontend/lib/features/answer/survey_start_screen.dart, frontend/lib/features/answer/survey_answer_screen.dart,
  frontend/lib/features/answer/answer_repository.dart, backend/apps/api/urls.py, backend/apps/api/views.py
  (SurveyDetailView, DraftView, SubmitResponseView), backend/apps/api/exceptions.py, backend/services/question_service.py,
  backend/services/response_service.py, backend/services/analysis_service.py, backend/repositories/ (survey, question,
  draft, response, analysis), backend/infrastructure/huggingface_client.py, backend/config/settings.py (CELERY_ENABLED)
Date / version: 2026-11-13, develop commit d3d2db2
```

The start screen loads the survey and the draft, the answer screen saves the draft each time the respondent moves to
another question, and Send stores the response in one transaction. Sentiment analysis then runs inside the same
request, after the commit (K-02, today's behaviour; `USE_CELERY` is false by default).

```mermaid
sequenceDiagram
    actor R as Respondent
    participant SS as SurveyStartScreen (Flutter screen)
    participant AS as SurveyAnswerScreen (Flutter screen)
    participant AR as AnswerRepository (app repository)
    participant V as SurveyDetailView, DraftView, SubmitResponseView (API view, Presentation)
    participant QS as QuestionService (service, Business)
    participant RS as ResponseService (service, Business)
    participant AN as AnalysisService (service, Business)
    participant DR as Survey, Question, Draft, Response, Analysis repositories (repository, Data Source)
    participant DB as PostgreSQL
    participant HF as HuggingFaceClient (gateway, Data Source)

    R->>SS: Open a survey from the eligible list
    par Survey
        SS->>AR: survey(id)
        AR->>V: GET /api/v1/surveys/{id}/
        V->>QS: get_response_form(user, id)
        QS->>DR: SurveyRepository.find_by_id(id)
        DR->>DB: SELECT FROM surveys
        DR-->>QS: survey
        QS->>QS: respondent, survey exists, can_accept_responses, targeting match
        QS->>DR: QuestionRepository.find_by_survey_id_with_options(id)
        DR->>DB: SELECT questions, question_options
        DR-->>QS: questions with options
        QS-->>V: survey and questions in order_index order
        V-->>AR: 200 survey detail
        AR-->>SS: SurveyDetail
    and Draft
        SS->>AR: draft(id)
        AR->>V: GET /api/v1/surveys/{id}/draft/
        V->>RS: get_draft(user, id)
        RS->>RS: ensure_can_answer(user, id)
        RS->>DR: DraftRepository.find(survey_id, respondent_id)
        DR->>DB: SELECT FROM response_drafts
        DB-->>DR: row or no row
        alt Draft exists
            RS-->>V: draft
            V-->>AR: 200 survey_id, answers, started_at, updated_at
            AR-->>SS: SurveyDraft
        else No draft (normal case)
            RS-->>V: raise DraftNotFound
            V-->>AR: 404 draft_not_found
            AR-->>SS: null
        end
    end

    alt Draft found
        SS-->>R: Continue or Start over
        alt Continue (resume)
            R->>SS: Continue
            SS->>AS: open at the first unanswered question (review page when all are answered)
        else Start over
            R->>SS: Start over and confirm
            SS->>AR: deleteDraft(id)
            AR->>V: DELETE /api/v1/surveys/{id}/draft/
            V->>RS: delete_draft(user, id)
            RS->>DR: DraftRepository.delete(survey_id, respondent_id)
            DR->>DB: DELETE FROM response_drafts
            V-->>AR: 204
            SS->>AS: open at question 1
        end
    else No draft
        R->>SS: Start survey
        SS->>AS: open at question 1
    end

    loop Each move to another question (Next or Back)
        R->>AS: Answer and move
        opt Answers differ from the last saved ones
            AS->>AR: saveDraft(id, answers)
            AR->>V: PUT /api/v1/surveys/{id}/draft/ answers (full replace)
            V->>RS: save_draft(user, id, answers)
            RS->>RS: ensure_can_answer, check each answer (nothing required yet)
            RS->>DR: DraftRepository.find, then save(draft)
            DR->>DB: INSERT or UPDATE response_drafts
            DB-->>DR: stored row
            V-->>AR: 200 draft
        end
    end

    opt Respondent leaves before sending
        R->>AS: Back
        AS->>AR: saveDraft(id, answers) with the last answers
        AR->>V: PUT /api/v1/surveys/{id}/draft/
        V-->>AR: 200 draft
        AS-->>SS: close, the start screen loads the survey and the draft again
        Note over R,SS: Later the respondent opens the survey again and resumes with Continue
    end

    R->>AS: Send answers on the review page
    AS->>AR: submit(id, answers), timeout 60 s
    AR->>V: POST /api/v1/surveys/{id}/responses/ answers
    V->>RS: submit_response(user, id, answers)
    RS->>RS: ensure_can_answer(user, id)
    RS->>DR: ResponseRepository.has_response_for_survey(survey_id, respondent_id)
    DR->>DB: SELECT EXISTS FROM responses
    alt Already answered
        RS-->>V: raise DuplicateResponse
        V-->>AR: 409 duplicate_response
        AR-->>AS: ApiException
        AS-->>R: You already answered this survey (after a lost connection the app shows the sent screen)
    else Not answered yet
        RS->>RS: check required answers and each answer against its question type
        alt Answer invalid
            RS-->>V: raise ValidationError
            V-->>AR: 400 validation_error
            AS-->>R: Mark the questions that need an answer
        else Answers valid
            critical transaction.atomic
                RS->>DR: DraftRepository.find(survey_id, respondent_id)
                DR->>DB: SELECT FROM response_drafts
                RS->>DR: ResponseRepository.save(Response with started_at = draft.started_at)
                DR->>DB: INSERT INTO responses
                loop Each answer with a value
                    RS->>DR: ResponseRepository.save_answer(answer)
                    DR->>DB: INSERT INTO answers
                end
                RS->>DR: DraftRepository.delete(survey_id, respondent_id)
                DR->>DB: DELETE FROM response_drafts
                RS->>RS: on_commit(_dispatch_sentiment_analysis) when there is an open-text answer
                DB-->>RS: COMMIT
            option Parallel submit hits unique_response_per_survey_respondent
                DB-->>RS: IntegrityError, ROLLBACK
                RS-->>V: raise DuplicateResponse
                V-->>AR: 409 duplicate_response
            end
            opt Open-text answers (after COMMIT, inside the same request)
                RS->>AN: analyze_open_text_answers(response_id)
                loop Each open-text answer
                    AN->>DR: AnalysisRepository save result with status PENDING
                    DR->>DB: INSERT INTO sentiment_analysis_results
                    AN->>HF: analyze_sentiment(answer_value)
                    HF->>HF: POST to the Hugging Face model URL
                    alt HTTP 200 with a known label
                        HF-->>AN: label, score
                        AN->>AN: mark_completed(label, score), status COMPLETED
                    else HTTP 402 or other failure
                        HF-->>AN: raise ExternalAnalysisServiceError
                        AN->>AN: mark_failed(), status FAILED
                    end
                    AN->>DR: AnalysisRepository.update(result)
                    DR->>DB: UPDATE sentiment_analysis_results
                end
            end
            RS-->>V: response
            V-->>AR: 201 id, survey_id, submitted_at
            AR-->>AS: SubmitResult
            AS-->>R: Sent screen
        end
    end
```

Notes from the code:

- `ensure_can_answer` checks, in order: respondent (403 `unauthorized_action`), survey exists (404 `survey_not_found`),
  published (409 `not_editable`), targeting match (403 `unauthorized_action`), not answered yet (409
  `duplicate_response`). The draft requests run all five checks. The survey detail request runs the first four only
  (`QuestionService._ensure_respondent_can_answer`).
- The answer screen sends at most one draft request at a time; newer answers wait and follow it.
- The on-commit callback is registered with `robust=True`: an error inside the analysis is logged and the response
  stays stored. A Hugging Face failure never changes the 201 answer; it only stores FAILED.
- With `USE_CELERY=true` the callback sends the work to a Celery task instead and the request does not wait. This is
  not the default and is not drawn.

## Legend

| Symbol | Meaning |
|---|---|
| Stick figure | Actor: the person using the app. |
| Box at the top | Lifeline: one object or group of classes; the label names the class and its layer. |
| Solid arrow (`->>`) | Call or HTTP request. |
| Dashed arrow (`-->>`) | Return value, raised exception or HTTP response with its status code. |
| Arrow back to the same lifeline | Internal step of that object. |
| `par` / `and` frame | The parts run at the same time (`Future.wait` in the app). |
| `alt` / `else` frame | Alternatives: only one branch runs, chosen by the condition in brackets. |
| `opt` frame | Optional part: runs only when the condition holds. |
| `loop` frame | Repeated part. |
| `critical` / `option` frame | Database transaction (`transaction.atomic`): all steps commit together; the `option` part is the failure that rolls everything back. |
| Note | Comment over the lifelines it names. |
| `200`, `201`, `204`, `400`, `404`, `409` | HTTP status code; the word after it is the `error.code` of the shared error body. |
| HTTP 402 | Status code returned by Hugging Face (payment required) when the account cannot run the model. |
