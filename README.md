# Smart Survey Platform

Smart Survey Platform is a web-based survey management system designed to create targeted surveys, collect responses from eligible respondents, and analyze results using statistical dashboards and AI-based sentiment analysis.

The platform was developed as an academic software engineering project with a strong focus on layered architecture, separation of concerns, clean service logic, and traceable requirements.

---

## Project Overview

Traditional survey systems often distribute surveys without ensuring that the right respondents participate. They may also lack duplicate-response prevention, automated analysis of open-text answers, and platform-level administrative reporting.

Smart Survey Platform addresses these limitations by providing:

- Role-based access for service providers, respondents, and administrators.
- Demographic profile management for respondents.
- Survey targeting based on demographic criteria.
- Eligible survey filtering.
- Duplicate-response prevention.
- AI-based sentiment analysis for open-text answers.
- Detailed survey analytics for service providers.
- System-level reports for administrators.

---

## Graduation 1 (in progress)

Graduation 1 (October 2026 to January 2027) extends the platform with a Flutter mobile app for respondents,
richer targeting, a response-quality engine, and sentiment analysis of Arabic (MSA) and English open answers.
The team works with Kanban: a defined workflow with work-in-progress limits on the
[GitHub Projects board](https://github.com/users/Yaman8almatar/projects/1), and a release reviewed with the
supervisors every two weeks, starting 2026-11-02. The workflow and its policies are in
[`planning/KANBAN.md`](planning/KANBAN.md).

- Built so far: the respondent REST API (`/api/v1/`, JWT) and the Flutter respondent app with login,
  registration, the eligible-survey list and logout. How to run it: [`frontend/README.md`](frontend/README.md).
- Planned: requirements FR-01..FR-20, tracked as issues in the
  [Product Backlog](https://github.com/users/Yaman8almatar/projects/1).
- Seminar 1 slides: [`documentation/graduation-1/`](documentation/graduation-1/).
- Diagrams: [`diagrams/`](diagrams/README.md).
- Releases: `v1.0-junior-final` (junior project), `v1.1-iteration0` (Iteration 0, Seminar 1),
  `v1.1.1` and `v1.1.2` (patch releases).

---

## Main User Roles

### Service Provider

A service provider can:

- Create surveys.
- Update survey data before publication.
- Add questions to surveys.
- Define targeting criteria.
- Publish and close surveys.
- View detailed analytics for owned surveys.

### Respondent

A respondent can:

- Create an account with demographic data.
- Manage the demographic profile.
- View eligible surveys.
- Participate in eligible surveys.
- View surveys already answered.

### System Administrator

A system administrator can:

- Manage user accounts.
- Activate, suspend, or soft-delete accounts.
- View system reports.
- Monitor users, surveys, responses, and platform activity.

---

## Core Features

- User registration and authentication.
- Role-based navigation and authorization.
- Survey creation and management.
- Multiple question types:
  - Multiple choice.
  - Rating scale.
  - Open-text questions.
- Targeting criteria based on demographic data.
- Eligible surveys for respondents.
- Single-response enforcement per respondent per survey.
- AI sentiment analysis for open-text answers.
- Provider analytics dashboard.
- Admin system reports with charts.
- Answered surveys page for respondents.
- Survey action restrictions based on survey status.

---

## Architecture

The system is a three-tier client-server system (client, Django application server, PostgreSQL). Inside the
Django server the code is organised in three logical layers (Fowler, *Patterns of Enterprise Application
Architecture*):

```text
Presentation Layer   DRF API views + serializers (REST, for the Flutter app)
                     Django views + templates (MVT, for provider and admin pages)
Business Layer       services/        Service Layer pattern: business rules and workflows
Data Source Layer    repositories/    Repository pattern: all database queries (Django ORM)
                     infrastructure/  Gateway pattern: HuggingFaceClient, the external sentiment API
Domain Model         apps/core/models Django models (Active Record), used by the business and data source layers
```

This structure separates responsibilities and prevents direct database access from the presentation layer.

---

## Main Services

- `AuthenticationService`
- `ProfileService`
- `SurveyService`
- `QuestionService`
- `TargetingService`
- `ResponseService`
- `AnalysisService`
- `AdminService`

---

## Main Repositories

- `UserRepository`
- `ProfileRepository`
- `SurveyRepository`
- `QuestionRepository`
- `TargetingRepository`
- `ResponseRepository`
- `AnalysisRepository`

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Django | Web framework |
| PostgreSQL | Relational database |
| Django ORM | Database interaction |
| Bootstrap | User interface styling |
| Chart.js | Data visualization |
| Hugging Face API | Sentiment analysis |
| pytest | Service-layer testing |
| Docker | Local PostgreSQL environment |
| Git / GitHub | Version control |
| Environment Variables | Sensitive configuration management |

---

## AI Integration

The system integrates with the Hugging Face Inference API to analyze open-text answers.

Open-text responses are processed through:

```text
AnalysisService -> HuggingFaceClient -> Hugging Face API
```

The external API call is isolated inside `infrastructure/huggingface_client.py`, which keeps the service layer independent from external communication details.

Sentiment results are normalized into:

- Positive
- Neutral
- Negative

If the AI service fails, the system preserves the submitted answers and marks the analysis result as failed instead of losing the response data.

---

## Database Main Entities

The system uses the following main data entities:

- User
- RespondentProfile
- Survey
- Question
- QuestionOption
- TargetingCriteria
- Response
- Answer
- SentimentAnalysisResult

---

## Survey Lifecycle

A survey can have one of the following statuses:

```text
DRAFT -> PUBLISHED -> CLOSED
```

Action rules:

- Draft surveys can be edited and prepared.
- Published surveys can receive responses from eligible respondents.
- Closed surveys no longer accept responses.
- Invalid actions are hidden or blocked based on the current survey status.

---

## Admin Reports

The administrator dashboard includes platform-level reports such as:

- Total users.
- Total surveys.
- Total responses.
- Active surveys.
- Users by type.
- Surveys by status.
- Responses over time.
- User growth over time.
- Most active surveys.

These reports provide an operational overview of the platform.

---

## Project Structure

The repository is a monorepo: the Django backend lives in `backend/` and the Flutter respondent app in `frontend/`.

```text
smart-survey-platform/
├── backend/                  Django project (run all Python commands from here)
│   ├── manage.py
│   ├── config/               settings, URLs, ASGI/WSGI
│   ├── apps/                 Django apps: views, forms, URLs, models, migrations
│   ├── core/                 shared enums and exceptions
│   ├── services/             business rules and workflows
│   ├── repositories/         database access (Django ORM)
│   ├── infrastructure/       external integrations (Hugging Face API)
│   ├── templates/  static/
│   ├── tests/                service-layer tests (pytest)
│   ├── requirements.txt  pytest.ini  .env.example
├── frontend/                 Flutter respondent app (Android and web)
├── diagrams/                 Diagram exports (PNG): class diagram, use case diagrams
├── documentation/
│   ├── junior/               junior project documents
│   └── graduation-1/         Graduation 1 report and slides
├── planning/                 status, Kanban workflow, API contract, backend audit
├── .github/workflows/        CI (Django CI, Flutter CI)
├── docker-compose.yml        PostgreSQL 15 for local development
├── CONTRIBUTING.md           workflow, branching and commit rules
└── README.md
```

---

## Local Setup

Commands are for Windows PowerShell. Requirements: Python 3.11, Docker Desktop, Git.

### 1. Clone the repository

```powershell
git clone https://github.com/Yaman8almatar/smart-survey-platform.git
cd smart-survey-platform
```

### 2. Create the virtual environment (repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
```

### 3. Configure environment variables

```powershell
copy backend\.env.example backend\.env
```

Edit `backend\.env` and set `SECRET_KEY` and `HF_API_TOKEN`. The database values already match
`docker-compose.yml` (`DB_HOST=127.0.0.1`, `DB_PORT=5432`). Never commit `backend\.env`.

### 4. Start PostgreSQL (repository root)

```powershell
docker compose up -d
```

### 5. Migrate, seed and run (from backend)

```powershell
cd backend
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```


---

## Demo Accounts

```text
Admin:
admin@demo.com / DemoPass123!

Service Provider:
provider@demo.com / DemoPass123!

Respondent:
respondent@demo.com / DemoPass123!
```

---

## Testing

Run all tests (services, repositories, settings and views):

```bash
cd backend
python -m pytest tests -q
```

Run Django checks:

```bash
python manage.py check
```

---

## Project Quality Rules

The project follows these engineering rules:

- Views delegate business operations to services.
- Services contain business rules and workflow logic.
- Repositories isolate database queries.
- External AI calls are isolated in a gateway class (`infrastructure/huggingface_client.py`) in the data source layer.
- Models represent persistent domain entities.
- Duplicate responses are blocked by business logic.
- Survey actions are restricted by survey status.
- Sensitive configuration is stored in environment variables.

---

## Academic Notes

This project was developed as a software engineering academic project. It applies:

- Requirements analysis.
- Use case modeling.
- Activity diagrams.
- Class diagrams.
- ERD and relational schema.
- Layered architecture.
- Service-layer testing.
- AI integration.
- Admin reporting and analytics.

---

## Future Work

Possible future improvements include:

- Export analytics and reports to PDF or Excel.
- Add notification system for newly published surveys.
- Add more advanced targeting criteria.
- Support multilingual sentiment analysis.
- Add audit logs for administrator actions.
- Add advanced filtering for analytics dashboards.

---

## License

This project is developed for academic purposes.
