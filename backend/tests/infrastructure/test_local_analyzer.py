"""LocalTransformersAnalyzer without torch: the `loader` seam and fakes stand in for the model."""

import hashlib
import math
import sys
from types import SimpleNamespace

import pytest

from core.exceptions import AnalysisConfigError, AnalysisUnavailable, ExternalAnalysisServiceError
from infrastructure import local_analyzer
from infrastructure.local_analyzer import LocalTransformersAnalyzer

WEIGHTS = b"fake weights"
WEIGHTS_SHA = hashlib.sha256(WEIGHTS).hexdigest()
M4_LABELS = {0: "negative", 1: "neutral", 2: "positive"}


class FakeLogits:
    def __init__(self, row):
        self.row = row

    def tolist(self):
        return [self.row]


class FakeModel:
    def __init__(self, row=(0.1, 0.2, 3.0), error=None):
        self.row = list(row)
        self.error = error

    def __call__(self, **encoded):
        if self.error:
            raise self.error
        return SimpleNamespace(logits=FakeLogits(self.row))


class FakeTokenizer:
    def __init__(self):
        self.calls = []

    def __call__(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return {"input_ids": [1, 2, 3]}


class CountingLoader:
    def __init__(self, model=None, id2label=None):
        self.calls = 0
        self.tokenizer = FakeTokenizer()
        self.model = model or FakeModel()
        self.id2label = M4_LABELS if id2label is None else id2label

    def __call__(self):
        self.calls += 1
        return self.tokenizer, self.model, self.id2label


@pytest.fixture
def model_dir(tmp_path):
    folder = tmp_path / "m4"
    folder.mkdir()
    (folder / "model.safetensors").write_bytes(WEIGHTS)
    return folder


@pytest.fixture
def hash_calls(monkeypatch):
    calls = []
    real = local_analyzer.file_sha256

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(local_analyzer, "file_sha256", counting)
    return calls


def make(model_dir, loader=None, sha=WEIGHTS_SHA):
    return LocalTransformersAnalyzer(str(model_dir), "org/m4", sha, loader=loader)


@pytest.mark.parametrize(
    ("row", "label"),
    [((4.0, 0.0, 0.0), "NEGATIVE"), ((0.0, 4.0, 0.0), "NEUTRAL"), ((0.0, 0.0, 4.0), "POSITIVE")],
)
def test_maps_each_label_and_returns_the_softmax_probability(model_dir, row, label):
    loader = CountingLoader(model=FakeModel(row))

    result = make(model_dir, loader).analyze_sentiment("Some text")

    expected = math.exp(4.0) / (math.exp(4.0) + 2)
    assert result["label"] == label
    assert isinstance(result["score"], float)
    assert result["score"] == pytest.approx(expected)


def test_tokenises_like_t2_and_loads_once(model_dir, hash_calls):
    loader = CountingLoader()
    analyzer = make(model_dir, loader)

    analyzer.analyze_sentiment("First")
    analyzer.analyze_sentiment("Second")

    assert loader.calls == 1
    assert len(hash_calls) == 1
    assert loader.tokenizer.calls[0] == (
        "First",
        {"truncation": True, "max_length": 512, "return_tensors": "pt"},
    )


def test_model_id_does_not_load(model_dir):
    loader = CountingLoader()

    assert make(model_dir, loader).model_id == "org/m4"
    assert loader.calls == 0


@pytest.mark.parametrize(
    "id2label",
    [
        {0: "neg", 1: "neu", 2: "pos"},
        {0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"},
        {0: "very negative", 1: "negative", 2: "neutral", 3: "positive", 4: "very positive"},
    ],
)
def test_an_unknown_label_set_fails_with_config(model_dir, id2label):
    with pytest.raises(AnalysisConfigError):
        make(model_dir, CountingLoader(id2label=id2label)).analyze_sentiment("Text")


def test_upper_case_m4_labels_with_string_keys_are_accepted(model_dir):
    loader = CountingLoader(id2label={"0": "NEGATIVE", "1": "Neutral", "2": "positive"})

    assert make(model_dir, loader).analyze_sentiment("Text")["label"] == "POSITIVE"


@pytest.mark.parametrize("case", ["no_folder", "no_weights", "blank_sha", "wrong_sha"])
def test_missing_files_and_unchecked_weights_fail_with_config(model_dir, case):
    path, sha = model_dir, WEIGHTS_SHA
    if case == "no_folder":
        path = model_dir.parent / "missing"
    elif case == "no_weights":
        (model_dir / "model.safetensors").unlink()
    elif case == "blank_sha":
        sha = "  "
    else:
        sha = "0" * 64
    loader = CountingLoader()

    with pytest.raises(AnalysisConfigError) as exc_info:
        make(path, loader, sha=sha).analyze_sentiment("Text")

    assert exc_info.value.error_code == "config"
    assert loader.calls == 0


def test_a_blank_model_path_fails_with_config():
    with pytest.raises(AnalysisConfigError, match="SENTIMENT_MODEL_PATH"):
        LocalTransformersAnalyzer("", "org/m4", WEIGHTS_SHA).analyze_sentiment("Text")


def test_after_a_wrong_sha_a_second_call_fails_at_once(model_dir, hash_calls):
    loader = CountingLoader()
    analyzer = make(model_dir, loader, sha="f" * 64)

    for _ in range(2):
        with pytest.raises(AnalysisConfigError):
            analyzer.analyze_sentiment("Text")

    assert len(hash_calls) == 1
    assert loader.calls == 0


def test_after_a_failed_load_a_second_call_fails_at_once(model_dir, hash_calls):
    loader = CountingLoader(id2label={0: "bad", 1: "labels", 2: "here"})
    analyzer = make(model_dir, loader)

    for _ in range(2):
        with pytest.raises(AnalysisConfigError, match="Unexpected model labels"):
            analyzer.analyze_sentiment("Text")

    assert len(hash_calls) == 1
    assert loader.calls == 1


def test_a_missing_runtime_fails_with_config_and_names_requirements_ml(model_dir, monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)  # the runtime import now raises ImportError

    with pytest.raises(AnalysisConfigError, match="requirements-ml.txt"):
        make(model_dir).analyze_sentiment("Text")


def test_an_inference_error_becomes_unavailable(model_dir):
    loader = CountingLoader(model=FakeModel(error=RuntimeError("out of memory")))

    with pytest.raises(AnalysisUnavailable) as exc_info:
        make(model_dir, loader).analyze_sentiment("Text")

    assert exc_info.value.error_code == "unavailable"


@pytest.mark.parametrize("text", ["", "   ", None, 42])
def test_empty_or_non_string_text_fails_like_the_client(model_dir, text):
    loader = CountingLoader()

    with pytest.raises(ExternalAnalysisServiceError) as exc_info:
        make(model_dir, loader).analyze_sentiment(text)

    assert type(exc_info.value) is ExternalAnalysisServiceError
    assert exc_info.value.error_code == "error"
    assert loader.calls == 0
