from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.enums import Gender

REGISTRATION_GENDERS = [Gender.MALE, Gender.FEMALE]


class UserSerializer(serializers.Serializer):
    """Public account data of the signed-in user."""

    id = serializers.IntegerField(source="user_id", read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.CharField(read_only=True)
    role = serializers.CharField(source="user_type", read_only=True)


class ProfileSerializer(serializers.Serializer):
    """Demographic profile used for survey targeting (read and update)."""

    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=REGISTRATION_GENDERS)
    region = serializers.CharField(max_length=255)
    interests = serializers.CharField()


class RegisterSerializer(ProfileSerializer):
    """Respondent registration input; business rules stay in AuthenticationService."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenRequestSerializer(serializers.Serializer):
    """Email and password login input."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenPairSerializer(serializers.Serializer):
    """Access and refresh JWT pair."""

    access = serializers.CharField()
    refresh = serializers.CharField()


class EligibleSurveySerializer(serializers.Serializer):
    """One eligible survey row with its question count."""

    id = serializers.IntegerField(source="survey.survey_id")
    title = serializers.CharField(source="survey.title")
    description = serializers.CharField(source="survey.description")
    question_count = serializers.IntegerField()


class OptionSerializer(serializers.Serializer):
    """One answer choice of a multiple-choice question."""

    id = serializers.IntegerField(source="option_id")
    text = serializers.CharField(source="option_text")


class QuestionSerializer(serializers.Serializer):
    """One question of the response form."""

    id = serializers.IntegerField(source="question_id")
    text = serializers.CharField(source="question_text")
    type = serializers.CharField(source="question_type")
    is_required = serializers.BooleanField()
    order_index = serializers.IntegerField()
    options = OptionSerializer(many=True)
    rating_values = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_rating_values(self, question):
        """Offer rating values only for rating-scale questions."""
        return question["rating_values"] if question["is_rating_scale"] else []


class SurveyDetailSerializer(serializers.Serializer):
    """Survey header with its ordered response-form questions."""

    id = serializers.IntegerField(source="survey.survey_id")
    title = serializers.CharField(source="survey.title")
    description = serializers.CharField(source="survey.description")
    questions = QuestionSerializer(many=True)


class AnswerSerializer(serializers.Serializer):
    """One submitted answer; type rules per question are checked by ResponseService."""

    question_id = serializers.IntegerField()
    answer_value = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, trim_whitespace=False
    )
    rating_value = serializers.IntegerField(required=False, allow_null=True)
    selected_option_id = serializers.IntegerField(required=False, allow_null=True)


class SubmitResponseSerializer(serializers.Serializer):
    """Body of a survey submission."""

    answers = AnswerSerializer(many=True)


class ResponseCreatedSerializer(serializers.Serializer):
    """Receipt of a stored response."""

    id = serializers.IntegerField(source="response_id")
    survey_id = serializers.IntegerField()
    submitted_at = serializers.DateTimeField()


class AnsweredSurveySerializer(serializers.Serializer):
    """One row of the answered survey history."""

    survey_id = serializers.IntegerField()
    title = serializers.CharField(source="survey_title")
    description = serializers.CharField(source="survey_description")
    submitted_at = serializers.DateTimeField()


class ErrorBodySerializer(serializers.Serializer):
    """Error details shared by every endpoint."""

    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
    )


class ErrorSerializer(serializers.Serializer):
    """Error envelope returned for every failed request."""

    error = ErrorBodySerializer()
