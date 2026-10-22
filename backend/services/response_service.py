from apps.core.models import Answer, Response
from core.enums import QuestionType, UserType
from core.exceptions import (
    DuplicateResponse,
    NotEditable,
    QuestionNotFound,
    SurveyNotFound,
    UnauthorizedAction,
    ValidationError,
)
from repositories.question_repository import QuestionRepository
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services.analysis_service import AnalysisService
from services.targeting_service import TargetingService


class ResponseService:
    """Handles Response submission, answer validation, and analysis triggering."""

    MIN_RATING = 1
    MAX_RATING = 5

    def __init__(
        self,
        survey_repository=None,
        question_repository=None,
        response_repository=None,
        targeting_service=None,
        analysis_service=None,
    ):
        """Wire repositories and services used by response submission workflows."""
        self.survey_repository = survey_repository or SurveyRepository()
        self.question_repository = question_repository or QuestionRepository()
        self.response_repository = response_repository or ResponseRepository()
        self.targeting_service = targeting_service or TargetingService()
        self.analysis_service = analysis_service or AnalysisService()

    def submit_response(self, respondent_user, survey_id, answers):
        """Validate and store a respondent survey submission with its answers."""
        self._ensure_respondent(respondent_user)

        survey = self.survey_repository.find_by_id(survey_id)
        if survey is None:
            raise SurveyNotFound("Survey not found.")

        if not survey.can_accept_responses():
            raise NotEditable("Responses are allowed only for published surveys.")

        if not self.targeting_service.match_respondent_to_survey(
            respondent_user,
            survey_id,
        ):
            raise UnauthorizedAction("Respondent is not eligible for this survey.")

        # Enforce the single-response rule before storing answers.
        if self.validate_duplicate_response(respondent_user, survey_id):
            raise DuplicateResponse("Respondent already submitted this survey.")

        questions = list(self.question_repository.find_by_survey_id(survey_id))
        question_map = {question.question_id: question for question in questions}
        answer_map = self._build_answer_map(answers)

        self._validate_required_answers(questions, answer_map)
        self._validate_all_answer_data(question_map, answer_map)

        response = self.response_repository.save(
            Response(survey=survey, respondent=respondent_user)
        )

        for answer_data in answer_map.values():
            question = question_map.get(answer_data.get("question_id"))
            if question is None:
                raise QuestionNotFound("Question does not belong to this survey.")

            answer = self._build_answer(response, question, answer_data)
            if answer is not None:
                self.response_repository.save_answer(answer)

        if response.has_open_text_answers():
            # Sentiment analysis is triggered only after open-text answers are stored.
            self.analysis_service.analyze_open_text_answers(response.response_id)

        return response

    def validate_duplicate_response(self, respondent_user, survey_id):
        """Prevent a respondent from submitting more than one response to the same survey."""
        return self.response_repository.has_response_for_survey(
            survey_id,
            respondent_user.user_id,
        )

    def get_answered_surveys(self, respondent_user):
        """Return surveys already answered by the respondent without enabling resubmission."""
        self._ensure_respondent_for_answered_surveys(respondent_user)
        responses = self.response_repository.find_by_respondent_id(
            respondent_user.user_id,
        )

        return [
            {
                "survey_id": response.survey.survey_id,
                "survey_title": response.survey.title,
                "survey_description": response.survey.description,
                "submitted_at": response.submitted_at,
            }
            for response in responses
        ]

    def _ensure_respondent(self, user):
        """Ensure only respondents can submit survey responses."""
        if user.user_type != UserType.RESPONDENT:
            raise UnauthorizedAction("Only respondents can submit survey responses.")

    def _ensure_respondent_for_answered_surveys(self, user):
        """Ensure only respondents can view their answered survey history."""
        if user.user_type != UserType.RESPONDENT:
            raise UnauthorizedAction("Only respondents can view answered surveys.")

    def _build_answer_map(self, answers):
        """Index submitted answers by question and reject duplicate answer entries."""
        if not isinstance(answers, list):
            raise ValidationError("Answers must be provided as a list.")

        answer_map = {}
        for answer_data in answers:
            if not isinstance(answer_data, dict):
                raise ValidationError("Each answer must be a dictionary.")

            question_id = answer_data.get("question_id")
            if question_id is None:
                raise ValidationError("Each answer must include question_id.")

            if question_id in answer_map:
                raise ValidationError("Duplicate answers for the same question are invalid.")

            answer_map[question_id] = answer_data

        return answer_map

    def _validate_required_answers(self, questions, answer_map):
        """Ensure every required question has valid submitted data."""
        for question in questions:
            if not question.is_required:
                continue

            answer_data = answer_map.get(question.question_id)
            if answer_data is None:
                raise ValidationError("Required questions must have answers.")

            self._validate_answer_data(question, answer_data, required=True)

    def _validate_all_answer_data(self, question_map, answer_map):
        """Validate that submitted answer data matches each question type."""
        for answer_data in answer_map.values():
            question = question_map.get(answer_data.get("question_id"))
            if question is None:
                raise QuestionNotFound("Question does not belong to this survey.")

            self._validate_answer_data(question, answer_data, required=question.is_required)

    def _build_answer(self, response, question, answer_data):
        """Create the Answer object that matches the question type."""
        if not question.is_required and self._is_empty_optional_answer(question, answer_data):
            return None

        if question.question_type == QuestionType.OPEN_TEXT:
            return Answer(
                response=response,
                question=question,
                answer_value=answer_data.get("answer_value"),
            )

        if question.question_type == QuestionType.RATING_SCALE:
            return Answer(
                response=response,
                question=question,
                rating_value=answer_data.get("rating_value"),
            )

        selected_option = self._find_question_option(
            question.question_id,
            answer_data.get("selected_option_id"),
        )
        return Answer(
            response=response,
            question=question,
            selected_option=selected_option,
        )

    def _validate_answer_data(self, question, answer_data, required):
        """Route answer validation to the correct question-type validator."""
        if question.question_type == QuestionType.OPEN_TEXT:
            self._validate_open_text_answer(answer_data, required)
        elif question.question_type == QuestionType.RATING_SCALE:
            self._validate_rating_answer(answer_data, required)
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            self._validate_multiple_choice_answer(question, answer_data, required)
        else:
            raise ValidationError("Unsupported question type.")

    def _validate_open_text_answer(self, answer_data, required):
        """Validate open-text answer fields."""
        if answer_data.get("selected_option_id") is not None:
            raise ValidationError("Open-text answers must not use selected_option.")
        if answer_data.get("rating_value") is not None:
            raise ValidationError("Open-text answers must not use rating_value.")

        answer_value = answer_data.get("answer_value")
        if answer_value is not None and not isinstance(answer_value, str):
            raise ValidationError("Open-text answers must use text answer_value.")

        if required and (not isinstance(answer_value, str) or not answer_value.strip()):
            raise ValidationError("Required open-text answers must not be blank.")

    def _validate_rating_answer(self, answer_data, required):
        """Validate rating-scale answer fields."""
        if answer_data.get("selected_option_id") is not None:
            raise ValidationError("Rating-scale answers must not use selected_option.")
        if answer_data.get("answer_value") is not None:
            raise ValidationError("Rating-scale answers must not use answer_value.")

        rating_value = answer_data.get("rating_value")
        if required or rating_value is not None:
            if (
                type(rating_value) is not int
                or rating_value < self.MIN_RATING
                or rating_value > self.MAX_RATING
            ):
                raise ValidationError("Rating value must be an integer from 1 to 5.")

    def _validate_multiple_choice_answer(self, question, answer_data, required):
        """Validate multiple-choice answer fields and selected option ownership."""
        if answer_data.get("answer_value") is not None:
            raise ValidationError("Multiple-choice answers must not use answer_value.")
        if answer_data.get("rating_value") is not None:
            raise ValidationError("Multiple-choice answers must not use rating_value.")

        selected_option_id = answer_data.get("selected_option_id")
        if required and selected_option_id is None:
            raise ValidationError("Multiple-choice answers must include selected_option.")

        if selected_option_id is not None:
            self._find_question_option(question.question_id, selected_option_id)

    def _find_question_option(self, question_id, selected_option_id):
        """Return the selected option only if it belongs to the question."""
        for option in self.question_repository.find_options_by_question_id(question_id):
            if option.option_id == selected_option_id:
                return option

        raise ValidationError("Selected option must belong to the answered question.")

    def _is_empty_optional_answer(self, question, answer_data):
        """Return whether an optional answer has no meaningful submitted value."""
        if question.question_type == QuestionType.OPEN_TEXT:
            answer_value = answer_data.get("answer_value")
            return answer_value is None or not answer_value.strip()
        if question.question_type == QuestionType.RATING_SCALE:
            return answer_data.get("rating_value") is None
        return answer_data.get("selected_option_id") is None
