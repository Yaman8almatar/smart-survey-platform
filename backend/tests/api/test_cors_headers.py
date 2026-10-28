import pytest

from config import settings as config_settings

ALLOW_ORIGIN = "Access-Control-Allow-Origin"
PATH = "/api/v1/schema/"


@pytest.fixture
def debug_cors(settings):
    # pytest-django forces DEBUG off, so apply the value DEBUG=True would give.
    settings.CORS_ALLOWED_ORIGIN_REGEXES = config_settings.API_CORS_LOCAL_ORIGIN_REGEXES


@pytest.mark.django_db
@pytest.mark.parametrize(
    "origin", ["http://localhost:5000", "http://127.0.0.1:5000"]
)
def test_flutter_web_origin_gets_cors_header_in_debug(client, debug_cors, origin):
    response = client.get(PATH, HTTP_ORIGIN=origin)

    assert response[ALLOW_ORIGIN] == origin


@pytest.mark.django_db
@pytest.mark.parametrize(
    "origin",
    ["http://evil.com", "https://localhost:5000", "http://localhost.evil.com:5000"],
)
def test_foreign_origin_gets_no_cors_header(client, debug_cors, origin):
    response = client.get(PATH, HTTP_ORIGIN=origin)

    assert ALLOW_ORIGIN not in response


@pytest.mark.django_db
def test_local_origin_gets_no_cors_header_when_debug_is_off(client, settings):
    settings.CORS_ALLOWED_ORIGIN_REGEXES = []

    response = client.get(PATH, HTTP_ORIGIN="http://localhost:5000")

    assert ALLOW_ORIGIN not in response


@pytest.mark.django_db
def test_preflight_allows_authorization_header(client, debug_cors):
    response = client.options(
        "/api/v1/me/",
        HTTP_ORIGIN="http://localhost:5000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
    )

    assert response.status_code == 200
    assert response[ALLOW_ORIGIN] == "http://localhost:5000"
    assert "authorization" in response["Access-Control-Allow-Headers"].lower()
