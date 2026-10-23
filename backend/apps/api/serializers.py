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
