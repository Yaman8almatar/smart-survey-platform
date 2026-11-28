"""M4 run locally on the CPU (FR-05, DESIGN-INC2 P-11, P-16).

No Django import: evaluation/check_deployed.py imports this module outside Django.
torch and transformers are imported only on the first analysis, so the web process,
CI and the Docker image never need them.
"""

import contextlib
import hashlib
import math
import re
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
WEIGHTS_FILE = "model.safetensors"
MANIFEST_DIR = Path(__file__).resolve().parent / "model_manifests"
_MODEL_ID = re.compile(r"[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)?")
_MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)")


def manifest_path(model_id):
    """Return the committed manifest file for a model id ("org/name" -> org__name.sha256)."""
    return MANIFEST_DIR / f"{model_id.replace('/', '__')}.sha256"


def read_manifest(model_id):
    """Return {file name: SHA-256} from the model's committed manifest (sha256sum format).

    Blank lines and lines starting with "#" are ignored. An unknown model id, a missing file or
    any malformed line gives {}, which the analyzer refuses on first use.
    """
    if not isinstance(model_id, str) or not _MODEL_ID.fullmatch(model_id):
        return {}
    try:
        text = manifest_path(model_id).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    manifest = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _MANIFEST_LINE.fullmatch(line)
        if not match or match.group(2) in manifest or match.group(2).startswith("."):
            return {}
        manifest[match.group(2)] = match.group(1)
    return manifest


def file_sha256(path):
    """Return the hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalTransformersAnalyzer:
    """Labels text with a local sequence-classification model, loaded once per process.

    Every file in `manifest` ({file name: SHA-256}, from read_manifest) must exist in the model
    folder and match its value, so only the files T-2 evaluated are loaded.
    `loader` is a test seam: a callable returning (tokenizer, model, id2label) that replaces
    importing the runtime and loading from disk.
    """

    def __init__(self, model_path, model_id, manifest, loader=None):
        """Store the configuration; nothing is read or loaded here."""
        self.model_path = (model_path or "").strip() if isinstance(model_path, str) else model_path
        self._model_id = model_id
        self.manifest = dict(manifest or {})
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
        """Check every manifest file's SHA-256, then load the tokenizer and the model."""
        if not self.manifest:
            raise AnalysisConfigError(
                f"No valid manifest {manifest_path(self._model_id or '').name} in "
                "backend/infrastructure/model_manifests/; unchecked model files are refused."
            )
        if WEIGHTS_FILE not in self.manifest:
            raise AnalysisConfigError(f"The manifest does not list {WEIGHTS_FILE}; unchecked weights are refused.")
        if not self.model_path:
            raise AnalysisConfigError("SENTIMENT_MODEL_PATH is not configured.")
        folder = Path(self.model_path)
        if not folder.is_dir():
            raise AnalysisConfigError(f"Model folder not found: {folder}")
        for name in self.manifest:
            if not (folder / name).is_file():
                raise AnalysisConfigError(f"Model file not found: {folder / name}")
        for name, expected in self.manifest.items():
            if file_sha256(folder / name) != expected:
                raise AnalysisConfigError(
                    f"{name} does not match the manifest; these are not the evaluated model files."
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
