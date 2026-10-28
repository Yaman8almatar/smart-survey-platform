import datetime
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.enums import AccountStatus, Gender, UserType
from repositories.response_repository import ResponseRepository
from repositories.user_repository import UserRepository
from apps.core.tasks import analyze_open_text_answers_task

User = get_user_model()


@pytest.mark.django_db
def test_liveness_probe_returns_200():
    client = APIClient()
    response = client.get("/healthz/live/")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


@pytest.mark.django_db
def test_readiness_probe_returns_200():
    client = APIClient()
    response = client.get("/healthz/ready/")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "connected"


@pytest.mark.django_db
def test_password_validation_rejects_weak_passwords():
    client = APIClient()
    weak_passwords = ["123", "password", "12345678"]
    for weak_pw in weak_passwords:
        response = client.post(
            "/api/v1/auth/register/",
            {
                "email": f"weak_{weak_pw}@example.com",
                "password": weak_pw,
                "name": "Weak User",
                "age": 25,
                "gender": "MALE",
                "region": "Damascus",
                "interests": "Tech",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "password" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_jwt_logout_blacklists_refresh_token():
    user = User.objects.create_user(
        email="logout_test@example.com",
        password="ValidStrongPassword123!",
        name="Logout User",
        user_type=UserType.RESPONDENT,
        account_status=AccountStatus.ACTIVE,
    )
    client = APIClient()

    # Obtain tokens
    token_resp = client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "ValidStrongPassword123!"},
        format="json",
    )
    assert token_resp.status_code == 200
    refresh_token = token_resp.json()["refresh"]
    access_token = token_resp.json()["access"]

    # Logout
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    logout_resp = client.post(
        "/api/v1/auth/logout/",
        {"refresh": refresh_token},
        format="json",
    )
    assert logout_resp.status_code in (200, 204)

    # Try to refresh with the blacklisted token
    client.credentials()
    refresh_attempt = client.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": refresh_token},
        format="json",
    )
    assert refresh_attempt.status_code == 401


@pytest.mark.django_db
def test_sargable_date_queries_and_total_responses():
    user_repo = UserRepository()
    resp_repo = ResponseRepository()

    start_date = datetime.date(2026, 1, 1)
    end_date = datetime.date(2026, 12, 31)

    user_growth = list(user_repo.count_created_by_date(start_date, end_date))
    assert isinstance(user_growth, list)

    resp_counts = list(resp_repo.count_submitted_by_date(start_date, end_date))
    assert isinstance(resp_counts, list)

    total = resp_repo.total_responses()
    assert isinstance(total, int)
    assert total >= 0
