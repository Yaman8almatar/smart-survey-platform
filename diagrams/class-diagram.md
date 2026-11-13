# Class diagram: domain model (Increment 1)

```
Basis: team convention (diagrams/README.md: requirement IDs and layer names)
Source of truth: backend/apps/core/models/ (ten model files), backend/core/enums.py
Date / version: 2026-11-13, develop commit d3d2db2
```

The ten domain classes of `apps.core`, their key attributes, the methods that hold business rules, and the
enumerations they use. Attribute types are the Python types of the Django fields.

```mermaid
classDiagram
    direction TB

    class User {
        +int user_id
        +str name
        +str email
        +UserType user_type
        +AccountStatus account_status
        +bool is_active
        +datetime created_at
        +activate()
        +suspend()
        +mark_deleted()
    }

    class RespondentProfile {
        +int profile_id
        +int age
        +Gender gender
        +Governorate region
        +list~Interest~ interests
        +Education education
        +Occupation occupation
        +MaritalStatus marital_status
        +datetime updated_at
        +clean()
        +update_profile(age, gender, region, interests, education, occupation, marital_status)
        +is_complete() bool
        +completion_percent() int
    }

    class Survey {
        +int survey_id
        +str title
        +str description
        +SurveyStatus status
        +datetime created_at
        +datetime? published_at
        +datetime? closed_at
        +clean()
        +publish()
        +close()
        +can_edit() bool
        +can_delete() bool
        +can_accept_responses() bool
    }

    class TargetingCriteria {
        +int criteria_id
        +Gender? gender
        +int? age_min
        +int? age_max
        +Governorate? region
        +is_open_to_all() bool
    }

    class Question {
        +int question_id
        +str question_text
        +QuestionType question_type
        +bool is_required
        +int order_index
        +is_choice_based() bool
        +is_open_text() bool
    }

    class QuestionOption {
        +int option_id
        +str option_text
        +int order_index
    }

    class Response {
        +int response_id
        +datetime? started_at
        +datetime submitted_at
        +add_answer(answer) Answer
        +has_open_text_answers() bool
    }

    class ResponseDraft {
        +int draft_id
        +list~dict~ answers
        +datetime started_at
        +datetime updated_at
    }

    class Answer {
        +int answer_id
        +str? answer_value
        +int? rating_value
        +is_textual() bool
        +is_rating_based() bool
        +is_option_based() bool
        +requires_sentiment_analysis() bool
    }

    class SentimentAnalysisResult {
        +int result_id
        +SentimentLabel? sentiment_label
        +float? sentiment_score
        +AnalysisStatus status
        +datetime? analyzed_at
        +mark_completed(label, score, analyzed_at)
        +mark_failed()
    }

    class UserType {
        <<enumeration>>
        SERVICE_PROVIDER
        RESPONDENT
        ADMIN
    }

    class AccountStatus {
        <<enumeration>>
        ACTIVE
        SUSPENDED
        DELETED
    }

    class SurveyStatus {
        <<enumeration>>
        DRAFT
        PUBLISHED
        CLOSED
    }

    class QuestionType {
        <<enumeration>>
        MULTIPLE_CHOICE
        RATING_SCALE
        OPEN_TEXT
    }

    class AnalysisStatus {
        <<enumeration>>
        PENDING
        COMPLETED
        FAILED
    }

    class SentimentLabel {
        <<enumeration>>
        POSITIVE
        NEGATIVE
        NEUTRAL
    }

    class Gender {
        <<enumeration>>
        MALE
        FEMALE
        ANY
    }

    class Governorate {
        <<enumeration>>
        15 values
    }

    class Interest {
        <<enumeration>>
        12 values
    }

    class Education {
        <<enumeration>>
        7 values
    }

    class Occupation {
        <<enumeration>>
        9 values
    }

    class MaritalStatus {
        <<enumeration>>
        5 values
    }

    User "1" *-- "0..1" RespondentProfile : respondent_profile
    User "1" *-- "0..*" Survey : provider
    User "1" *-- "0..*" Response : respondent
    User "1" *-- "0..*" ResponseDraft : respondent
    Survey "1" *-- "0..1" TargetingCriteria : criteria
    Survey "1" *-- "0..*" Question : questions
    Survey "1" *-- "0..*" Response : responses
    Survey "1" *-- "0..*" ResponseDraft : drafts
    Question "1" *-- "0..*" QuestionOption : options
    Question "1" *-- "0..*" Answer : answers
    Response "1" *-- "0..*" Answer : answers
    Answer "0..*" --> "0..1" QuestionOption : selected_option
    Answer "1" *-- "0..1" SentimentAnalysisResult : sentiment_analysis_result

    User ..> UserType
    User ..> AccountStatus
    Survey ..> SurveyStatus
    Question ..> QuestionType
    SentimentAnalysisResult ..> AnalysisStatus
    SentimentAnalysisResult ..> SentimentLabel
    RespondentProfile ..> Gender
    RespondentProfile ..> Governorate
    RespondentProfile ..> Interest
    RespondentProfile ..> Education
    RespondentProfile ..> Occupation
    RespondentProfile ..> MaritalStatus
    TargetingCriteria ..> Gender
    TargetingCriteria ..> Governorate

    note for Governorate "Long code lists: the values are in backend/core/enums.py"
    note for RespondentProfile "completion_percent: share of 7 details filled. is_complete: age, gender, region, interests set"
```

## Business rules held by the classes

| Class | Method | Rule (from the code) |
|---|---|---|
| User | `activate`, `suspend`, `mark_deleted` | Set `account_status` and `is_active` together; delete is a soft delete. |
| RespondentProfile | `clean` | Only a RESPONDENT user may own a profile; `Gender.ANY` is not allowed. |
| RespondentProfile | `is_complete` | True when age, gender, a valid governorate and at least one interest are set. |
| RespondentProfile | `completion_percent` | Filled share of the seven `COMPLETION_FIELDS`, rounded, in percent. |
| Survey | `clean` | The provider must be a SERVICE_PROVIDER user. |
| Survey | `can_edit` | Only a DRAFT survey can be edited. |
| Survey | `can_delete` | Only a DRAFT or CLOSED survey can be deleted. |
| Survey | `can_accept_responses` | Only a PUBLISHED survey accepts responses. |
| TargetingCriteria | `is_open_to_all` | No gender (or ANY), no age limits and no region. |
| Answer | `requires_sentiment_analysis` | Only an answer to an OPEN_TEXT question is analysed. |
| SentimentAnalysisResult | `mark_completed`, `mark_failed` | COMPLETED stores label and score; FAILED clears them and stamps `analyzed_at`. |

## Legend

| Symbol | Meaning |
|---|---|
| Box with three parts | Class: name, attributes, methods. |
| Box marked `<<enumeration>>` | Enumeration (Django `TextChoices` in backend/core/enums.py). Short lists show every value; long lists show the number of values. |
| `+` | Public member. |
| `name()` and `name() type` | Method, with its return type when it returns a value. |
| `type?` | Optional attribute: the field allows NULL. |
| `list~T~` | List of T: `list~Interest~` is a PostgreSQL array, `list~dict~` is a JSON list. |
| Line with filled diamond (`*--`) | Composition: the part is deleted with the whole (`on_delete=CASCADE`). The diamond is on the whole. Team convention: a part with two CASCADE parents (Response, ResponseDraft, Answer) shows both. |
| Line with open arrow (`-->`) | Association: Answer knows its selected option; deleting the option sets the link to NULL (`on_delete=SET_NULL`). |
| Dashed arrow (`..>`) | Dependency: the attribute type is that enumeration. |
| `1`, `0..1`, `0..*` | Multiplicity at that end of the line. |
| Label on a line | The Django field or `related_name` that holds the link. |
| Note box | Comment attached to a class. |
