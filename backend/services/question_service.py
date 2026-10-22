from django.db import transaction

from apps.core.models import Question, QuestionOption
from core.enums import QuestionType, UserType
from core.exceptions import (
    NotEditable,
    QuestionNotFound,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.question_repository import QuestionRepository
from repositories.survey_repository import SurveyRepository


class QuestionService:
    """Handles Question management for provider-owned draft surveys."""

    RATING_VALUES = [1, 2, 3, 4, 5]

    def __init__(self, survey_repository=None, question_repository=None):
        """Wire repositories used by question management workflows."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.question_repository = question_repository or QuestionRepository()

    def add_question(
        self,
        provider_user,
        survey_id,
        text,
        question_type,
        is_required,
        order_index,
    ):
        """Add a question to an owned draft survey."""
        survey = self._get_owned_draft_survey(provider_user, survey_id)
        self._validate_question_data(text, order_index)

        question = Question(
            survey=survey,
            question_text=text,
            question_type=question_type,
            is_required=is_required,
            order_index=order_index,
        )
        return self.question_repository.save(question)

    def add_question_with_options(
        self,
        provider_user,
        survey_id,
        text,
        question_type,
        is_required,
        order_index,
        options=None,
    ):
        """Create a survey question and persist its options when the type is multiple choice."""
        normalized_options = self._normalize_options(options)

        with transaction.atomic():
            # Keep question and multiple-choice options in a single save workflow.
            question = self.add_question(
                provider_user,
                survey_id,
                text,
                question_type,
                is_required,
                order_index,
            )

            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                self.add_question_options(
                    provider_user,
                    question.question_id,
                    normalized_options,
                )
            elif normalized_options:
                raise ValidationError(
                    "Options are only allowed for multiple-choice questions."
                )

            return question

    def add_question_options(self, provider_user, question_id, options):
        """Add options to an owned draft multiple-choice question."""
        question = self._get_question_for_owned_draft_survey(provider_user, question_id)

        if question.question_type != QuestionType.MULTIPLE_CHOICE:
            raise ValidationError("Options are only allowed for multiple-choice questions.")

        self._validate_options(options)

        saved_options = []
        for index, option_text in enumerate(options):
            option = QuestionOption(
                question=question,
                option_text=option_text,
                order_index=index,
            )
            saved_options.append(self.question_repository.save_option(option))
        return saved_options

    def update_question(self, provider_user, question_id, text, is_required, order_index):
        """Update an owned draft survey question."""
        question = self._get_question_for_owned_draft_survey(provider_user, question_id)
        self._validate_question_data(text, order_index)

        question.question_text = text
        question.is_required = is_required
        question.order_index = order_index
        return self.question_repository.update(question)

    def delete_question(self, provider_user, question_id):
        """Delete an owned draft survey question."""
        question = self._get_question_for_owned_draft_survey(provider_user, question_id)
        return self.question_repository.delete(question.question_id)

    def get_response_form_questions(self, survey_id):
        """Return ordered question and option data for the response form."""
        questions = sorted(
            self.question_repository.find_by_survey_id(survey_id),
            key=lambda question: (question.order_index, question.question_id),
        )
        return [self._response_form_question(question) for question in questions]

    def get_survey_question_rows(self, provider_user, survey_id):
        """Return ordered survey questions and options for the management page."""
        self._get_owned_survey(provider_user, survey_id)
        questions = sorted(
            self.question_repository.find_by_survey_id(survey_id),
            key=lambda question: (question.order_index, question.question_id),
        )
        return [self._survey_question_row(question) for question in questions]

    def _get_question_for_owned_draft_survey(self, provider_user, question_id):
        """Return a question after provider ownership and draft status checks."""
        self._ensure_service_provider(provider_user)

        question = self.question_repository.find_by_id(question_id)
        if question is None:
            raise QuestionNotFound("Question not found.")

        self._ensure_owner(provider_user, question.survey)
        self._ensure_draft_survey(question.survey)
        return question

    def _get_owned_draft_survey(self, provider_user, survey_id):
        """Return an owned survey only when questions are still editable."""
        survey = self._get_owned_survey(provider_user, survey_id)
        self._ensure_draft_survey(survey)
        return survey

    def _get_owned_survey(self, provider_user, survey_id):
        """Return a survey after provider ownership validation."""
        self._ensure_service_provider(provider_user)

        survey = self.survey_repository.find_by_id(survey_id)
        if survey is None:
            raise SurveyNotFound("Survey not found.")

        self._ensure_owner(provider_user, survey)
        return survey

    def _ensure_service_provider(self, user):
        """Ensure only service providers can manage questions."""
        if user.user_type != UserType.SERVICE_PROVIDER:
            raise UnauthorizedAction("Only service providers can manage questions.")

    def _ensure_owner(self, provider_user, survey):
        """Ensure the provider owns the survey being changed."""
        if survey.provider_id != provider_user.user_id:
            raise UnauthorizedAction("Only the survey owner can manage questions.")

    def _ensure_draft_survey(self, survey):
        """Ensure questions are changed only before survey publication."""
        if not survey.can_edit():
            raise NotEditable("Questions can only be managed for draft surveys.")

    def _validate_question_data(self, text, order_index):
        """Validate common question text and ordering rules."""
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("Question text must not be empty.")

        if type(order_index) is not int or order_index < 0:
            raise ValidationError("Order index must be a non-negative integer.")

    def _normalize_options(self, options):
        """Normalize option input into a clean list of option labels."""
        if options is None:
            return []

        if isinstance(options, str):
            return [
                option.strip()
                for option in options.splitlines()
                if option.strip()
            ]

        normalized_options = []
        for option in options:
            if isinstance(option, str):
                option = option.strip()
                if option:
                    normalized_options.append(option)
            else:
                normalized_options.append(option)
        return normalized_options

    def _validate_options(self, options):
        """Validate required multiple-choice option text."""
        if not options:
            raise ValidationError("Multiple-choice questions require option text.")

        for option_text in options:
            if not isinstance(option_text, str) or not option_text.strip():
                raise ValidationError("Option text must not be blank.")

    def _survey_question_row(self, question):
        """Build one provider-facing question row."""
        question_id = question.question_id
        return {
            "question_id": question_id,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "is_required": question.is_required,
            "order_index": question.order_index,
            "options": self._management_options(question_id),
            "id": question_id,
            "text": question.question_text,
            "type_label": question.get_question_type_display(),
            "required_label": "Required" if question.is_required else "Optional",
        }

    def _management_options(self, question_id):
        """Return ordered option data for the question management page."""
        options = sorted(
            self.question_repository.find_options_by_question_id(question_id),
            key=lambda option: (option.order_index, option.option_id),
        )
        return [
            {
                "option_id": option.option_id,
                "option_text": option.option_text,
                "order_index": option.order_index,
            }
            for option in options
        ]

    def _response_form_question(self, question):
        """Build one respondent-facing response form question."""
        question_id = question.question_id
        return {
            "question_id": question_id,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "is_required": question.is_required,
            "order_index": question.order_index,
            "options": self._response_form_options(question_id),
            "id": question_id,
            "text": question.question_text,
            "type_label": question.get_question_type_display(),
            "required_label": "Required" if question.is_required else "Optional",
            "is_open_text": question.question_type == QuestionType.OPEN_TEXT,
            "is_rating_scale": question.question_type == QuestionType.RATING_SCALE,
            "is_multiple_choice": question.question_type == QuestionType.MULTIPLE_CHOICE,
            "answer_name": f"answer_value_{question_id}",
            "rating_name": f"rating_value_{question_id}",
            "option_name": f"selected_option_id_{question_id}",
            "rating_values": self.RATING_VALUES,
        }

    def _response_form_options(self, question_id):
        """Return ordered option data for the respondent form."""
        options = sorted(
            self.question_repository.find_options_by_question_id(question_id),
            key=lambda option: (option.order_index, option.option_id),
        )
        return [
            {
                "option_id": option.option_id,
                "option_text": option.option_text,
                "order_index": option.order_index,
                "id": option.option_id,
                "text": option.option_text,
            }
            for option in options
        ]
