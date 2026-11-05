import pytest

from tests.api.conftest import PASSWORD

REGISTER_URL = "/api/v1/auth/register/"
TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"

pytestmark = pytest.mark.django_db

# (url, rate limit per minute, payload, normal status code below the limit)
SCOPES = {
    "auth_token": (TOKEN_URL, 10, {"email": "respondent@example.com", "password": "wrong"}, 401),
    "auth_refresh": (REFRESH_URL, 30, {"refresh": "not-a-token"}, 401),
    "auth_register": (REGISTER_URL, 5, {}, 400),
    "auth_logout": (LOGOUT_URL, 30, {"refresh": "not-a-token"}, 400),
}


def send(client, url, payload, times):
    return [client.post(url, payload, format="json") for _ in range(times)]


@pytest.mark.parametrize("scope", SCOPES)
def test_requests_up_to_the_limit_get_their_normal_answer(client, respondent, scope):
    url, limit, payload, normal_status = SCOPES[scope]

    responses = send(client, url, payload, limit)

    assert [r.status_code for r in responses] == [normal_status] * limit


@pytest.mark.parametrize("scope", SCOPES)
def test_request_after_the_limit_is_throttled(client, respondent, scope):
    url, limit, payload, _ = SCOPES[scope]
    send(client, url, payload, limit)

    response = client.post(url, payload, format="json")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"
    assert int(response["Retry-After"]) > 0


def test_using_up_login_does_not_block_token_refresh(client, respondent):
    url, limit, payload, _ = SCOPES["auth_token"]
    send(client, url, payload, limit + 1)

    login = client.post(TOKEN_URL, {"email": respondent.email, "password": PASSWORD}, format="json")
    refresh = client.post(REFRESH_URL, {"refresh": "not-a-token"}, format="json")

    assert login.status_code == 429
    assert refresh.status_code == 401


@pytest.mark.parametrize("url", ["/healthz/live/", "/healthz/ready/"])
def test_health_probes_are_not_throttled(client, url):
    responses = [client.get(url) for _ in range(120)]

    assert [r.status_code for r in responses] == [200] * 120
