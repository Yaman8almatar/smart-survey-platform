## Project
Smart Survey Platform — Smart Opinion Survey Platform

## Main Rule
This project must follow Layered Architecture strictly.

## Layers

### Presentation Layer
Includes:
- Django Views
- Django Forms
- Django Templates
- Bootstrap
- Chart.js

Rules:
- Views call Services only.
- Views must not call Repositories directly.
- Views must not contain business rules.
- Templates must not contain business logic.

### Service Layer
Located in:
- services/

Rules:
- Contains business logic only.
- May call Repositories.
- May call Infrastructure clients.
- Must not import Django request or response objects.

### Repository Layer
Located in:
- repositories/

Rules:
- Contains database access only.
- Uses Django ORM only.
- Must not contain business decisions.
- Must not call Services.

### Data Layer
Located in:
- apps/core/models/

Rules:
- Contains Django ORM models.
- Models may contain simple domain methods only.

### Infrastructure Layer
Located in:
- infrastructure/

Rules:
- External API clients only.
- Hugging Face API calls must be isolated here.

## Technology Stack
- Python 3.11
- Django 4.2
- PostgreSQL 15
- psycopg v3
- Django Templates
- Bootstrap 5
- Chart.js
- pytest
- pytest-django
- Hugging Face Inference API
- Docker Compose

## Required Django Apps
- apps/core
- apps/users
- apps/surveys
- apps/responses
- apps/analysis
- apps/admin_panel

## Required Top-Level Directories
- services/
- repositories/
- infrastructure/
- core/
- templates/
- static/
- tests/
- docs/
## Package Clarification

The project has two separate core-related locations:

1. Top-level `core/`
   - Shared non-Django package.
   - Contains `enums.py` and `exceptions.py`.

2. Django app `apps/core/`
   - Owns all ORM models.
   - Owns migrations.
   - Django app label must be `core`.

All domain models must be implemented under:

apps/core/models/

Other Django apps must not define domain models in the current implementation.

## Required Documentation Sources
Before implementing code, read:
- docs/functional_requirements.md
- docs/use_cases.md
- docs/architecture.md
- docs/class_diagram.mmd
- docs/erd.mmd
- docs/sequence_diagrams.md
- docs/implementation_decisions.md

## Enums
Create enums in core/enums.py using Django TextChoices:
- UserType: SERVICE_PROVIDER, RESPONDENT, ADMIN
- AccountStatus: ACTIVE, SUSPENDED, DELETED
- SurveyStatus: DRAFT, PUBLISHED, CLOSED
- QuestionType: MULTIPLE_CHOICE, RATING_SCALE, OPEN_TEXT
- Gender: MALE, FEMALE, ANY
- SentimentLabel: POSITIVE, NEGATIVE, NEUTRAL
- AnalysisStatus: PENDING, COMPLETED, FAILED

## Domain Rules
### User Model Strategy
- Use a custom Django User model.
- Implement it in `apps/core/models/user.py`.
- Extend `django.contrib.auth.models.AbstractUser`.
- Remove the default username field.
- Use email as the unique login identifier.
- Set `USERNAME_FIELD = "email"`.
- Configure `AUTH_USER_MODEL = "core.User"` in Django settings.

### Survey and Question Cardinality
- Draft surveys may have zero questions.
- Published surveys must have at least one question.
- This rule must be enforced in `SurveyService.publish_survey()`.

### SentimentAnalysisResult Nullability
- `sentiment_label`, `sentiment_score`, and `analyzed_at` are nullable.
- PENDING results have null label, score, and analyzed_at.
- COMPLETED results require label, score, and analyzed_at.
- FAILED results clear label and score.

### User
- User has name, email, password hash, user_type, account_status, created_at.
- email must be unique.
- account_status defaults to ACTIVE.
- DELETED means soft deleted.
- Suspended or deleted users cannot log in.

### RespondentProfile
- RespondentProfile belongs to exactly one User.
- Only RESPONDENT users may have RespondentProfile.
- RespondentProfile gender must not be ANY.

### Survey
- Survey belongs to a provider User.
- Provider must have user_type = SERVICE_PROVIDER.
- Survey status defaults to DRAFT.
- Survey can be edited only when status = DRAFT.
- Survey can be deleted only when status = DRAFT.
- Survey can accept responses only when status = PUBLISHED.
- publish() sets status = PUBLISHED and published_at = now.
- close() sets status = CLOSED and closed_at = now.

### Question
- Question belongs to Survey.
- Question supports MULTIPLE_CHOICE, RATING_SCALE, OPEN_TEXT.
- MULTIPLE_CHOICE questions require options.
- OPEN_TEXT questions do not use selected_option.
- RATING_SCALE questions use rating_value.

### TargetingCriteria
- TargetingCriteria belongs to exactly one Survey.
- Gender may be MALE, FEMALE, ANY, or null depending on implementation.
- Nullable criteria means no restriction.
- Matching must be implemented in Service Layer.

### Response
- Response belongs to Survey and Respondent User.
- Response must be unique per survey and respondent.
- Duplicate response must be rejected.

### Answer
- Answer belongs to Response and Question.
- answer_value is used for OPEN_TEXT.
- rating_value is used for RATING_SCALE.
- selected_option is used for MULTIPLE_CHOICE.
- Sentiment analysis is required only for OPEN_TEXT answers.

### SentimentAnalysisResult
- Belongs to one Answer.
- Created only for OPEN_TEXT answers.
- status can be PENDING, COMPLETED, FAILED.

## Mandatory Implementation Adjustments

1. Do not create ServiceProviderProfile.
   - Service providers are represented as User records with user_type = SERVICE_PROVIDER.

2. Add account_status to User.
   - Values: ACTIVE, SUSPENDED, DELETED.
   - DELETED is used for soft deletion.

3. Gender.ANY is not allowed for RespondentProfile.
   - Gender.ANY is allowed only in TargetingCriteria.

4. Answer must support:
   - answer_value for OPEN_TEXT.
   - rating_value for RATING_SCALE.
   - selected_option for MULTIPLE_CHOICE.

5. Do not implement custom SessionRepository or UserSession table.
   - Use Django authentication and session framework.

6. UC-14 must be implemented through ProfileService.
   - Web UI must not call ProfileRepository directly.

7. UC-15 must filter eligible surveys in the Service Layer.
   - The UI must display only the final list returned by SurveyService.get_eligible_surveys().

8. Add TargetingRepository even if it is not explicitly shown in the Class Diagram.
   - Reason: SURVEY_TARGETING_CRITERIA is a persistent ERD entity.

9. Use snake_case in Python implementation.
   - UML camelCase methods must be converted to snake_case.

## Security Rules
- Do not store plaintext passwords.
- Do not commit .env.
- Do not expose HF_API_TOKEN to templates or JavaScript.
- Use environment variables for secrets.
- Use Django authentication and password hashing.

## Code Commenting Rules
- Code comments must be written in English.
- Comments must be concise and useful.
- Add comments only for non-obvious business rules, validation decisions, external API handling, or complex queries.
- Do not write excessive comments.
- Do not repeat obvious code behavior in comments.
- Each public service method must have a concise English docstring.
- Docstrings should help locate the method responsibility during code review.

## Testing Rules
- Use pytest and pytest-django.
- Every Service must have tests.
- Tests must not call the real Hugging Face API.
- Run python manage.py check before every commit.
- Run pytest before every commit after tests exist.

## Naming Rules
- Python methods and variables use snake_case.
- Classes use PascalCase.
- Avoid Java-style method names.
- UML names like markDeleted must be implemented as mark_deleted.
- UML names like canEdit must be implemented as can_edit.
