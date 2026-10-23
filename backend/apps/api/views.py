from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from services.authentication_service import AuthenticationService
from services.profile_service import ProfileService

from .serializers import (
    ProfileSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    TokenRequestSerializer,
    UserSerializer,
)

AUTH_TAG = ["auth"]
ME_TAG = ["me"]


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
