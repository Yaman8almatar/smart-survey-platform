"""M4 run locally on the CPU (FR-05, DESIGN-INC2 P-11, P-16).

No Django import: evaluation/check_deployed.py imports this module outside Django.
torch and transformers are imported only on the first analysis, so the web process,
CI and the Docker image never need them.
"""

import contextlib
import hashlib
import math
from pathlib import Path

from core.exceptions import (
    AnalysisConfigError,
    AnalysisUnavailable,
    ExternalAnalysisServiceError,
)

EXPECTED_LABELS = {"negative", "neutral", "positive"}
MAX_TOKENS = 512  # as T-2 (evaluation/run_models.py)
HASH_CHUNK_BYTES = 1024 * 1024
RUNTIME_HINT = "Install the model runtime: .venv\\Scripts\\python.exe -m pip install -r backend\\requirements-ml.txt"


def file_sha256(path):
    """Return the hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalTransformersAnalyzer:
    """Labels text with a local sequence-classification model, loaded once per process.

    The weights file must match the SHA-256 that T-2 evaluated; any other weights are refused.
    `loader` is a test seam: a callable returning (tokenizer, model, id2label) that replaces
    importing the runtime and loading from disk.
    """

    def __init__(self, model_path, model_id, weights_sha256, weights_file="model.safetensors", loader=None):
        """Store the configuration; nothing is read or loaded here."""
        self.model_path = (model_path or "").strip() if isinstance(model_path, str) else model_path
        self._model_id = model_id
        self.weights_sha256 = (weights_sha256 or "").strip().lower()
        self.weights_file = weights_file
        self._loader = loader
        self._tokenizer = None
        self._model = None
        self._labels = None
        self._no_grad = contextlib.nullcontext
        self._load_error = None

    @property
    def model_id(self):
        """Return the configured model id without loading the model."""
        return self._model_id

    def analyze_sentiment(self, text):
        """Return {"label": POSITIVE|NEUTRAL|NEGATIVE, "score": probability} for one text."""
        if not isinstance(text, str) or not text.strip():
            raise ExternalAnalysisServiceError("Input text must not be empty.")
        self._ensure_loaded()

        try:
            with self._no_grad():
                encoded = self._tokenizer(
                    text, truncation=True, max_length=MAX_TOKENS, return_tensors="pt"
                )
                logits = self._model(**encoded).logits.tolist()[0]
            probabilities = _softmax(logits)
            index = max(range(len(probabilities)), key=probabilities.__getitem__)
            label = self._labels[index]
        except Exception as exc:  # noqa: BLE001 - any inference failure may pass on a later attempt
            raise AnalysisUnavailable("Local sentiment inference failed.") from exc

        return {"label": label.upper(), "score": float(probabilities[index])}

    def _ensure_loaded(self):
        """Load the model on first use; a failed load is remembered and raised again at once."""
        if self._model is not None:
            return
        if self._load_error is not None:
            raise AnalysisConfigError(self._load_error)
        try:
            self._load()
        except AnalysisConfigError as exc:
            self._load_error = str(exc)
            raise

    def _load(self):
        """Check the folder and the weights' SHA-256, then load the tokenizer and the model."""
        if not self.model_path:
            raise AnalysisConfigError("SENTIMENT_MODEL_PATH is not configured.")
        folder = Path(self.model_path)
        if not folder.is_dir():
            raise AnalysisConfigError(f"Model folder not found: {folder}")
        weights = folder / self.weights_file
        if not weights.is_file():
            raise AnalysisConfigError(f"Weights file not found: {weights}")
        if not self.weights_sha256:
            raise AnalysisConfigError("SENTIMENT_MODEL_SHA256 is not configured; unchecked weights are refused.")
        if file_sha256(weights) != self.weights_sha256:
            raise AnalysisConfigError(
                f"{weights.name} does not match SENTIMENT_MODEL_SHA256; these are not the evaluated weights."
            )

        if self._loader is not None:
            tokenizer, model, id2label = self._loader()
        else:
            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
            except ImportError as exc:
                raise AnalysisConfigError(f"The model runtime is missing. {RUNTIME_HINT}") from exc
            try:
                tokenizer = AutoTokenizer.from_pretrained(folder, local_files_only=True)
                model = AutoModelForSequenceClassification.from_pretrained(
                    folder, local_files_only=True, dtype=torch.float32
                ).eval()
            except Exception as exc:  # noqa: BLE001 - files that do not load never pass by waiting
                raise AnalysisConfigError(f"The model in {folder} could not be loaded: {exc}") from exc
            id2label = model.config.id2label
            self._no_grad = torch.no_grad

        labels = {int(key): str(value).lower() for key, value in id2label.items()}
        if sorted(labels) != [0, 1, 2] or set(labels.values()) != EXPECTED_LABELS:
            raise AnalysisConfigError(f"Unexpected model labels: {sorted(labels.values())}")

        self._labels = [labels[index] for index in range(3)]
        self._tokenizer = tokenizer
        self._model = model


def _softmax(values):
    """Return the softmax of a list of logits."""
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps)
    return [value / total for value in exps]
