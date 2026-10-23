from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from services.authentication_service import AuthenticationService
from services.profile_service import ProfileService
from services.question_service import QuestionService
from services.response_service import ResponseService
from services.survey_service import SurveyService

from .serializers import (
    AnsweredSurveySerializer,
    EligibleSurveySerializer,
    ErrorSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResponseCreatedSerializer,
    SubmitResponseSerializer,
    SurveyDetailSerializer,
    TokenPairSerializer,
    TokenRequestSerializer,
    UserSerializer,
)

AUTH_TAG = ["auth"]
ME_TAG = ["me"]
SURVEY_TAG = ["surveys"]


class PublicAPIView(APIView):
    """Base for endpoints that need no token (register, token)."""

    authentication_classes = []
    permission_classes = [AllowAny]


class RegisterView(PublicAPIView):
    @extend_schema(
        tags=AUTH_TAG,
        request=RegisterSerializer,
        responses={201: UserSerializer},
        summary="Register a respondent account",
    )
    def post(self, request):
        """Create a respondent and profile through AuthenticationService."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = AuthenticationService().register_respondent(
            data["name"],
            data["email"],
            data["password"],
            data["age"],
            data["gender"],
            data["region"],
            data["interests"],
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class TokenView(PublicAPIView):
    @extend_schema(
        tags=AUTH_TAG,
        request=TokenRequestSerializer,
        responses={200: TokenPairSerializer},
        summary="Exchange email and password for access and refresh tokens",
    )
    def post(self, request):
        """Authenticate through AuthenticationService, then issue a JWT pair."""
        serializer = TokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthenticationService().authenticate_user(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class TokenRefresh(TokenRefreshView):
    @extend_schema(tags=AUTH_TAG, summary="Exchange a refresh token for a new access token")
    def post(self, request, *args, **kwargs):
        """Return a new access token for a valid refresh token."""
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    @extend_schema(
        tags=ME_TAG,
        responses={200: UserSerializer},
        summary="Signed-in respondent account data",
    )
    def get(self, request):
        """Return the account data of the authenticated respondent."""
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    @extend_schema(
        tags=ME_TAG,
        responses={200: ProfileSerializer},
        summary="Read the demographic profile",
    )
    def get(self, request):
        """Return the demographic profile through ProfileService."""
        profile = ProfileService().get_profile(request.user)
        if profile is None:
            raise NotFound("Demographic profile not found.")
        return Response(ProfileSerializer(profile).data)

    @extend_schema(
        tags=ME_TAG,
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
        summary="Replace the demographic profile",
    )
    def put(self, request):
        """Create or update the demographic profile through ProfileService."""
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        profile = ProfileService().update_profile(
            request.user,
            data["age"],
            data["gender"],
            data["region"],
            data["interests"],
        )
        return Response(ProfileSerializer(profile).data)


class EligibleSurveysView(APIView):
    @extend_schema(
        tags=SURVEY_TAG,
        responses={200: EligibleSurveySerializer(many=True)},
        summary="Surveys matching the respondent profile that are not answered yet",
    )
    def get(self, request):
        """List eligible surveys through SurveyService."""
        items = SurveyService().get_eligible_survey_items(request.user)
        return Response(EligibleSurveySerializer(items, many=True).data)


class SurveyDetailView(APIView):
    @extend_schema(
        tags=SURVEY_TAG,
        responses={
            200: SurveyDetailSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
        summary="Survey with its questions and options",
    )
    def get(self, request, survey_id):
        """Return the response form through QuestionService."""
        form = QuestionService().get_response_form(request.user, survey_id)
        return Response(SurveyDetailSerializer(form).data)


SUBMIT_REQUEST_EXAMPLE = OpenApiExample(
    "Answer a choice, a rating and an open-text question",
    value={
        "answers": [
            {"question_id": 1, "selected_option_id": 2},
            {"question_id": 2, "rating_value": 4},
            {"question_id": 3, "answer_value": "Clear and quick."},
        ]
    },
    request_only=True,
)
SUBMIT_RESPONSE_EXAMPLE = OpenApiExample(
    "Stored response",
    value={"id": 17, "survey_id": 5, "submitted_at": "2026-10-23T09:30:00Z"},
    response_only=True,
    status_codes=["201"],
)
SUBMIT_ERROR_EXAMPLE = OpenApiExample(
    "Missing required answer",
    value={
        "error": {
            "code": "validation_error",
            "message": "Required questions must have answers.",
        }
    },
    response_only=True,
    status_codes=["400"],
)


class SubmitResponseView(APIView):
    @extend_schema(
        tags=SURVEY_TAG,
        request=SubmitResponseSerializer,
        responses={
            201: ResponseCreatedSerializer,
            400: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
        examples=[SUBMIT_REQUEST_EXAMPLE, SUBMIT_RESPONSE_EXAMPLE, SUBMIT_ERROR_EXAMPLE],
        summary="Submit answers to a survey",
    )
    def post(self, request, survey_id):
        """Validate and store the submission through ResponseService."""
        serializer = SubmitResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = [dict(answer) for answer in serializer.validated_data["answers"]]

        response = ResponseService().submit_response(request.user, survey_id, answers)
        return Response(
            ResponseCreatedSerializer(response).data,
            status=status.HTTP_201_CREATED,
        )


class AnsweredSurveysView(APIView):
    @extend_schema(
        tags=ME_TAG,
        responses={200: AnsweredSurveySerializer(many=True)},
        summary="Surveys the respondent already answered",
    )
    def get(self, request):
        """List answered survey history through ResponseService."""
        rows = ResponseService().get_answered_surveys(request.user)
        return Response(AnsweredSurveySerializer(rows, many=True).data)
