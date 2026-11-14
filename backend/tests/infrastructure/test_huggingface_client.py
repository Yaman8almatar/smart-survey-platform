import pytest
import requests

from core.exceptions import (
    AnalysisBadOutput,
    AnalysisConfigError,
    AnalysisPaymentRequired,
    AnalysisUnavailable,
    ExternalAnalysisServiceError,
)
from infrastructure.huggingface_client import HuggingFaceClient

MODEL_URL = "https://router.huggingface.co/hf-inference/models/org/sentiment-model"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, invalid_json=False):
        self.status_code = status_code
        self.payload = payload
        self.invalid_json = invalid_json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        if self.invalid_json:
            raise ValueError("not json")
        return self.payload


def client_with(monkeypatch, outcome):
    """Return a configured client whose requests.post returns or raises outcome."""

    def fake_post(*args, **kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr("infrastructure.huggingface_client.requests.post", fake_post)
    return HuggingFaceClient(api_token="test-token", model_url=MODEL_URL)


@pytest.mark.parametrize(
    ("outcome", "error_class", "error_code"),
    [
        (FakeResponse(402), AnalysisPaymentRequired, "payment_required"),
        (FakeResponse(401), AnalysisConfigError, "config"),
        (FakeResponse(403), AnalysisConfigError, "config"),
        (FakeResponse(404), AnalysisConfigError, "config"),
        (FakeResponse(429), AnalysisUnavailable, "unavailable"),
        (FakeResponse(503), AnalysisUnavailable, "unavailable"),
        (requests.Timeout("slow"), AnalysisUnavailable, "unavailable"),
        (requests.ConnectionError("down"), AnalysisUnavailable, "unavailable"),
        (FakeResponse(invalid_json=True), AnalysisBadOutput, "bad_output"),
        (FakeResponse(payload=[{"label": "MIXED", "score": 0.6}]), AnalysisBadOutput, "bad_output"),
        (FakeResponse(payload={"error": "x"}), AnalysisBadOutput, "bad_output"),
    ],
    ids=[
        "402",
        "401",
        "403",
        "404",
        "429",
        "503",
        "timeout",
        "connection-error",
        "invalid-json",
        "unknown-label",
        "bad-shape",
    ],
)
def test_each_gateway_error_has_its_class_and_code(monkeypatch, outcome, error_class, error_code):
    client = client_with(monkeypatch, outcome)

    with pytest.raises(error_class) as error:
        client.analyze_sentiment("Great service")

    assert error.value.error_code == error_code
    # Existing callers that catch the base class keep working.
    assert isinstance(error.value, ExternalAnalysisServiceError)


@pytest.mark.parametrize(
    ("api_token", "model_url"),
    [("", MODEL_URL), ("test-token", "")],
    ids=["missing-token", "missing-url"],
)
def test_missing_configuration_is_a_config_error(monkeypatch, api_token, model_url):
    def fail_post(*args, **kwargs):
        raise AssertionError("The gateway must not be called without configuration.")

    monkeypatch.setattr("infrastructure.huggingface_client.requests.post", fail_post)
    client = HuggingFaceClient(api_token=api_token, model_url=model_url)

    with pytest.raises(AnalysisConfigError) as error:
        client.analyze_sentiment("Great service")

    assert error.value.error_code == "config"


def test_model_id_is_the_url_part_after_models():
    client = HuggingFaceClient(api_token="t", model_url=MODEL_URL)

    assert client.model_id == "org/sentiment-model"


@pytest.mark.parametrize("model_url", ["", "https://example.com/model"])
def test_model_id_is_empty_without_a_models_url(model_url):
    client = HuggingFaceClient(api_token="t", model_url=model_url)

    assert client.model_id == ""
