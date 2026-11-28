"""LocalTransformersAnalyzer without torch: the `loader` seam and fakes stand in for the model."""

import hashlib
import math
import sys
from types import SimpleNamespace

import pytest

from core.exceptions import AnalysisConfigError, AnalysisUnavailable, ExternalAnalysisServiceError
from infrastructure import local_analyzer
from infrastructure.local_analyzer import LocalTransformersAnalyzer, read_manifest

M4_ID = "clapAI/roberta-base-multilingual-sentiment"
FILES = {
    "model.safetensors": b"fake weights",
    "tokenizer.json": b'{"fake": "tokenizer"}',
    "config.json": b'{"fake": "config"}',
    "tokenizer_config.json": b'{"fake": "tokenizer config"}',
    "special_tokens_map.json": b'{"fake": "special tokens"}',
}
MANIFEST = {name: hashlib.sha256(data).hexdigest() for name, data in FILES.items()}
M4_LABELS = {0: "negative", 1: "neutral", 2: "positive"}


def write_model(folder):
    """Write the five fake model files into a folder and return it."""
    folder.mkdir()
    for name, data in FILES.items():
        (folder / name).write_bytes(data)
    return folder


def manifest_text(manifest):
    return "".join(f"{digest}  {name}\n" for name, digest in manifest.items())


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
    return write_model(tmp_path / "m4")


@pytest.fixture
def manifest_dir(tmp_path, monkeypatch):
    folder = tmp_path / "manifests"
    folder.mkdir()
    monkeypatch.setattr(local_analyzer, "MANIFEST_DIR", folder)
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


def make(model_dir, loader=None, manifest=MANIFEST):
    return LocalTransformersAnalyzer(str(model_dir), "org/m4", manifest, loader=loader)


# --- the manifest file ---


def test_a_manifest_parses_and_ignores_comments_and_blank_lines(manifest_dir):
    (manifest_dir / "org__m4.sha256").write_text(
        "# M4, T-2\n\n" + manifest_text(MANIFEST) + "   \n# end\n", encoding="utf-8"
    )

    assert read_manifest("org/m4") == MANIFEST


@pytest.mark.parametrize(
    "line",
    [
        "abc  model.safetensors",  # not 64 hex digits
        f"{'A' * 64}  model.safetensors",  # upper case
        f"{'a' * 64} model.safetensors",  # one space
        f"{'a' * 64}  ",  # no file name
        f"{'a' * 64}  ../model.safetensors",  # a path, not a file name
        f"{'a' * 64}  config.json",  # a second line for the same file
    ],
)
def test_a_malformed_line_gives_an_empty_manifest(manifest_dir, line):
    (manifest_dir / "org__m4.sha256").write_text(manifest_text(MANIFEST) + line + "\n", encoding="utf-8")

    assert read_manifest("org/m4") == {}


@pytest.mark.parametrize("model_id", ["org/unknown", "", None, "../org/m4", "org\\..\\m4"])
def test_an_unknown_model_id_gives_an_empty_manifest(manifest_dir, model_id):
    (manifest_dir / "org__m4.sha256").write_text(manifest_text(MANIFEST), encoding="utf-8")

    assert read_manifest(model_id) == {}


def test_the_committed_m4_manifest_lists_exactly_the_evaluated_files():
    manifest = read_manifest(M4_ID)

    assert sorted(manifest) == sorted(FILES)
    assert manifest["model.safetensors"] == "01234f0e63a987c7bd768b5eb4a047343844de0414b14fa4f6625f88698c7771"
    assert manifest["tokenizer.json"] == "3a56def25aa40facc030ea8b0b87f3688e4b3c39eb8b45d5702b3a1300fe2a20"


# --- the analyzer ---


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
    assert sorted(path.name for path in hash_calls) == sorted(FILES)
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


def refusal_cases():
    """(case id, how to break it, text the error must contain)."""
    no_weights = {k: v for k, v in MANIFEST.items() if k != "model.safetensors"}
    cases = [
        ("empty_manifest", {"manifest": {}}, "org__m4.sha256"),
        ("no_weights_in_manifest", {"manifest": no_weights}, "model.safetensors"),
        ("no_folder", {"folder": "missing"}, "missing"),
    ]
    for name in FILES:
        cases.append((f"missing_{name}", {"delete": name}, name))
        cases.append((f"wrong_{name}", {"manifest": {**MANIFEST, name: "0" * 64}}, name))
    return cases


@pytest.mark.parametrize(("case", "change", "named"), refusal_cases(), ids=[c[0] for c in refusal_cases()])
def test_a_refused_manifest_or_file_fails_with_config_and_a_second_call_fails_at_once(
    model_dir, hash_calls, case, change, named
):
    path = model_dir.parent / change["folder"] if "folder" in change else model_dir
    if "delete" in change:
        (model_dir / change["delete"]).unlink()
    loader = CountingLoader()
    analyzer = make(path, loader, manifest=change.get("manifest", MANIFEST))

    with pytest.raises(AnalysisConfigError, match=named.replace(".", r"\.")) as exc_info:
        analyzer.analyze_sentiment("Text")
    hashed = len(hash_calls)
    with pytest.raises(AnalysisConfigError, match=named.replace(".", r"\.")):
        analyzer.analyze_sentiment("Text")

    assert exc_info.value.error_code == "config"
    assert len(hash_calls) == hashed  # the second call hashed nothing
    assert (hashed > 0) == case.startswith("wrong_")  # only a wrong value is found by hashing
    assert loader.calls == 0


def test_a_missing_file_is_found_before_any_file_is_hashed(model_dir, hash_calls):
    (model_dir / "special_tokens_map.json").unlink()

    with pytest.raises(AnalysisConfigError, match="special_tokens_map"):
        make(model_dir, CountingLoader()).analyze_sentiment("Text")

    assert hash_calls == []


def test_a_blank_model_path_fails_with_config():
    with pytest.raises(AnalysisConfigError, match="SENTIMENT_MODEL_PATH"):
        LocalTransformersAnalyzer("", "org/m4", MANIFEST).analyze_sentiment("Text")


def test_after_a_failed_load_a_second_call_fails_at_once(model_dir, hash_calls):
    loader = CountingLoader(id2label={0: "bad", 1: "labels", 2: "here"})
    analyzer = make(model_dir, loader)

    for _ in range(2):
        with pytest.raises(AnalysisConfigError, match="Unexpected model labels"):
            analyzer.analyze_sentiment("Text")

    assert len(hash_calls) == len(FILES)
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
