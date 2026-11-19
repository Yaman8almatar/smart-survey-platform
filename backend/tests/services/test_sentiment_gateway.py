"""The sentiment gateway: build_analyzer picks the adapter; building never loads a model (FR-05)."""

import pytest

from apps.core.models import SentimentAnalysisResult
from core.enums import AnalysisStatus, SentimentLabel
from core.exceptions import AnalysisConfigError
from infrastructure import local_analyzer, sentiment_analyzer
from infrastructure.huggingface_analyzer import HuggingFaceClient
from infrastructure.local_analyzer import LocalTransformersAnalyzer
from infrastructure.sentiment_analyzer import build_analyzer
from services.analysis_service import AnalysisService
from tests.infrastructure.test_local_analyzer import WEIGHTS, WEIGHTS_SHA, CountingLoader, FakeModel
from tests.services.test_analysis_worker import create_pending, create_survey


@pytest.fixture
def local_settings(settings, tmp_path):
    folder = tmp_path / "m4"
    folder.mkdir()
    (folder / "model.safetensors").write_bytes(WEIGHTS)
    settings.SENTIMENT_ANALYZER = "local"
    settings.SENTIMENT_MODEL_PATH = str(folder)
    settings.SENTIMENT_MODEL_ID = "clapAI/roberta-base-multilingual-sentiment"
    settings.SENTIMENT_MODEL_SHA256 = WEIGHTS_SHA
    return settings


@pytest.fixture
def counting_local(monkeypatch):
    """Make build_analyzer's local adapter use a counting fake loader; count hashing too."""
    loader = CountingLoader()
    hashes = []
    real_hash = local_analyzer.file_sha256

    def counting_hash(path):
        hashes.append(path)
        return real_hash(path)

    monkeypatch.setattr(local_analyzer, "file_sha256", counting_hash)
    monkeypatch.setattr(
        sentiment_analyzer,
        "LocalTransformersAnalyzer",
        lambda **kwargs: LocalTransformersAnalyzer(loader=loader, **kwargs),
    )
    return loader, hashes


def test_local_setting_builds_the_local_adapter_from_the_settings(local_settings):
    analyzer = build_analyzer()

    assert isinstance(analyzer, LocalTransformersAnalyzer)
    assert analyzer.model_path == local_settings.SENTIMENT_MODEL_PATH
    assert analyzer.weights_sha256 == WEIGHTS_SHA
    assert analyzer.model_id == "clapAI/roberta-base-multilingual-sentiment"


def test_huggingface_setting_builds_the_remote_client(settings):
    settings.SENTIMENT_ANALYZER = "huggingface"

    assert isinstance(build_analyzer(), HuggingFaceClient)


def test_an_unknown_setting_fails_with_config_on_first_use_only(settings):
    settings.SENTIMENT_ANALYZER = "openai"

    analyzer = build_analyzer()  # building and constructing the service do not fail
    AnalysisService(analyzer=analyzer)

    with pytest.raises(AnalysisConfigError, match="openai") as exc_info:
        analyzer.analyze_sentiment("Text")
    assert exc_info.value.error_code == "config"


def test_constructing_the_service_loads_nothing(local_settings, counting_local):
    loader, hashes = counting_local

    service = AnalysisService()

    assert isinstance(service.analyzer, LocalTransformersAnalyzer)
    assert loader.calls == 0
    assert hashes == []


@pytest.mark.django_db
def test_the_service_stores_the_local_analyzers_model_id_on_completion(local_settings, counting_local):
    loader, _ = counting_local
    loader.model = FakeModel((0.0, 0.0, 5.0))
    result = create_pending(create_survey("local"), "The staff were helpful.")

    AnalysisService().process_pending_batch()

    stored = SentimentAnalysisResult.objects.get(pk=result.pk)
    assert stored.status == AnalysisStatus.COMPLETED
    assert stored.sentiment_label == SentimentLabel.POSITIVE
    assert stored.model_id == "clapAI/roberta-base-multilingual-sentiment"
    assert stored.language == "en"
    assert loader.calls == 1


@pytest.mark.django_db
def test_wrong_weights_mark_the_result_failed_with_config(local_settings, counting_local):
    local_settings.SENTIMENT_MODEL_SHA256 = "0" * 64
    result = create_pending(create_survey("wrong-weights"), "The staff were helpful.")

    AnalysisService().process_pending_batch()

    stored = SentimentAnalysisResult.objects.get(pk=result.pk)
    assert stored.status == AnalysisStatus.FAILED
    assert stored.error_code == "config"
