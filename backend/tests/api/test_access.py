"""Access matrix: every endpoint except register/token needs a respondent token."""

import pytest

pytestmark = pytest.mark.django_db

# (method, path) pairs; ids are filled in by the test for survey routes.
PROTECTED_ENDPOINTS = [
    ("get", "/api/v1/me/"),
    ("get", "/api/v1/me/profile/"),
    (
        "put",
        "/api/v1/me/profile/",
    ),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_anonymous_gets_401_in_error_shape(client, method, path):
    response = getattr(client, method)(path, {}, format="json")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
@pytest.mark.parametrize("role", ["provider", "admin"])
def test_other_roles_get_403(client, authenticate, request, role, method, path):
    authenticate(request.getfixturevalue(role))

    response = getattr(client, method)(path, {}, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_malformed_bearer_token_gets_401(client):
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

    response = client.get("/api/v1/me/")

    assert response.status_code == 401
    assert set(response.json()) == {"error"}
