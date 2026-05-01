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

The system follows a layered architecture:

```text
Presentation Layer
Django Views, Templates, Bootstrap, Chart.js

Service Layer
Business rules and workflow orchestration

Repository Layer
Database access using Django ORM

Data Layer
Django models mapped to PostgreSQL tables

Infrastructure Layer
External integration with Hugging Face API
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

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/smart-survey-platform.git
cd smart-survey-platform
```

Replace the repository URL with your actual GitHub repository URL.

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file based on `.env.example`.

Example:

```env
SECRET_KEY=replace-this-secret-key
DEBUG=True

DB_NAME=smart_survey_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432

HF_API_TOKEN=your_huggingface_token
HF_SENTIMENT_MODEL_URL=https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment-latest
```

### 5. Start PostgreSQL with Docker

```bash
docker compose up -d
```

### 6. Apply Migrations

```bash
python manage.py migrate
```

### 7. Seed Demo Data

```bash
python manage.py seed_demo_data
```

### 8. Run the Development Server

```bash
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

Run service-layer tests:

```bash
pytest tests/services
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
- External AI calls are isolated in the infrastructure layer.
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
