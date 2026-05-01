from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    SentimentAnalysisResult,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import (
    AccountStatus,
    AnalysisStatus,
    Gender,
    QuestionType,
    SentimentLabel,
    SurveyStatus,
    UserType,
)


DEMO_PASSWORD = "DemoPass123!"
DEMO_SURVEY_TITLE = "Customer Experience Feedback"


class Command(BaseCommand):
    """Seeds demonstration accounts, survey data, answers, and analysis results."""

    help = "Seed local demo data for seminar demonstrations."

    @transaction.atomic
    def handle(self, *args, **options):
        """Create or update the local demo data set."""
        admin = self._upsert_user(
            email="admin@demo.com",
            name="Demo Admin",
            user_type=UserType.ADMIN,
        )
        provider = self._upsert_user(
            email="provider@demo.com",
            name="Demo Provider",
            user_type=UserType.SERVICE_PROVIDER,
        )
        respondent = self._upsert_user(
            email="respondent@demo.com",
            name="Demo Respondent",
            user_type=UserType.RESPONDENT,
        )

        profile = self._upsert_profile(respondent)
        survey = self._upsert_survey(provider)
        self._upsert_targeting_criteria(survey)

        open_text_question = self._upsert_question(
            survey=survey,
            text="What did you like most about the service?",
            question_type=QuestionType.OPEN_TEXT,
            order_index=1,
        )
        rating_question = self._upsert_question(
            survey=survey,
            text="How would you rate the overall service quality?",
            question_type=QuestionType.RATING_SCALE,
            order_index=2,
        )
        choice_question = self._upsert_question(
            survey=survey,
            text="Would you recommend this service to others?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=3,
        )
        yes_option = self._upsert_options(choice_question)["Yes"]

        response = self._upsert_response(survey, respondent)
        open_text_answer = self._upsert_open_text_answer(
            response,
            open_text_question,
            "The service was fast, clear, and easy to use.",
        )
        self._upsert_rating_answer(response, rating_question, 5)
        self._upsert_option_answer(response, choice_question, yes_option)
        self._upsert_sentiment_result(open_text_answer)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Demo accounts:")
        self.stdout.write(f"  Admin: {admin.email} / {DEMO_PASSWORD}")
        self.stdout.write(f"  Provider: {provider.email} / {DEMO_PASSWORD}")
        self.stdout.write(f"  Respondent: {respondent.email} / {DEMO_PASSWORD}")
        self.stdout.write("Demo profile:")
        self.stdout.write(f"  Respondent region: {profile.region}")
        self.stdout.write(f"  Respondent age: {profile.age}")
        self.stdout.write("Demo survey:")
        self.stdout.write(f"  Title: {survey.title}")
        self.stdout.write(f"  Status: {survey.get_status_display()}")

    def _upsert_user(self, email, name, user_type):
        """Create or update a demo user account."""
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)

        user.name = name
        user.user_type = user_type
        user.account_status = AccountStatus.ACTIVE
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _upsert_profile(self, respondent):
        """Create or update the demo respondent profile."""
        profile, _ = RespondentProfile.objects.update_or_create(
            user=respondent,
            defaults={
                "age": 24,
                "gender": Gender.MALE,
                "region": "Amman",
                "interests": "customer experience, digital services",
            },
        )
        return profile

    def _upsert_survey(self, provider):
        """Create or update the demo published survey."""
        survey = Survey.objects.filter(
            provider=provider,
            title=DEMO_SURVEY_TITLE,
        ).first()
        if survey is None:
            survey = Survey(provider=provider, title=DEMO_SURVEY_TITLE)

        survey.description = (
            "Demo survey used to evaluate service quality and customer satisfaction."
        )
        survey.status = SurveyStatus.PUBLISHED
        if survey.published_at is None:
            survey.published_at = timezone.now()
        survey.closed_at = None
        survey.save()
        return survey

    def _upsert_targeting_criteria(self, survey):
        """Create or update the demo survey targeting criteria."""
        return TargetingCriteria.objects.update_or_create(
            survey=survey,
            defaults={
                "gender": Gender.ANY,
                "age_min": 18,
                "age_max": 35,
                "region": "Amman",
            },
        )[0]

    def _upsert_question(self, survey, text, question_type, order_index):
        """Create or update one demo survey question."""
        question = Question.objects.filter(
            survey=survey,
            order_index=order_index,
        ).first()
        if question is None:
            question = Question(survey=survey, order_index=order_index)

        question.question_text = text
        question.question_type = question_type
        question.is_required = True
        question.save()
        return question

    def _upsert_options(self, question):
        """Create or update demo multiple-choice options."""
        options = {}
        for order_index, option_text in enumerate(["Yes", "No", "Maybe"], start=1):
            option = QuestionOption.objects.filter(
                question=question,
                order_index=order_index,
            ).first()
            if option is None:
                option = QuestionOption(question=question, order_index=order_index)

            option.option_text = option_text
            option.save()
            options[option_text] = option
        return options

    def _upsert_response(self, survey, respondent):
        """Create or return the demo respondent response."""
        response, _ = Response.objects.get_or_create(
            survey=survey,
            respondent=respondent,
        )
        return response

    def _upsert_open_text_answer(self, response, question, answer_value):
        """Create or update the demo open-text answer."""
        answer = self._get_or_create_answer(response, question)
        answer.answer_value = answer_value
        answer.rating_value = None
        answer.selected_option = None
        answer.save()
        return answer

    def _upsert_rating_answer(self, response, question, rating_value):
        """Create or update the demo rating answer."""
        answer = self._get_or_create_answer(response, question)
        answer.answer_value = None
        answer.rating_value = rating_value
        answer.selected_option = None
        answer.save()
        return answer

    def _upsert_option_answer(self, response, question, selected_option):
        """Create or update the demo multiple-choice answer."""
        answer = self._get_or_create_answer(response, question)
        answer.answer_value = None
        answer.rating_value = None
        answer.selected_option = selected_option
        answer.save()
        return answer

    def _get_or_create_answer(self, response, question):
        """Return an existing answer for a response/question pair or create one."""
        answer = Answer.objects.filter(response=response, question=question).first()
        if answer is None:
            answer = Answer(response=response, question=question)
        return answer

    def _upsert_sentiment_result(self, answer):
        """Create or update the demo completed sentiment result."""
        result, _ = SentimentAnalysisResult.objects.get_or_create(answer=answer)
        result.status = AnalysisStatus.COMPLETED
        result.sentiment_label = SentimentLabel.POSITIVE
        result.sentiment_score = 0.95
        result.analyzed_at = timezone.now()
        result.save()
        return result
