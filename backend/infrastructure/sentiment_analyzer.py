"""The one sentiment gateway the analysis service depends on (FR-05, DESIGN-INC2 P-11)."""

from typing import Protocol

from django.conf import settings

from core.exceptions import AnalysisConfigError
from infrastructure.huggingface_analyzer import HuggingFaceClient
from infrastructure.local_analyzer import LocalTransformersAnalyzer

ADAPTERS = ("local", "huggingface")


class SentimentAnalyzer(Protocol):
    """Labels one text; both adapters follow this contract."""

    @property
    def model_id(self) -> str:
        """The model name stored on each completed result."""

    def analyze_sentiment(self, text: str) -> dict:
        """Return {"label": "POSITIVE"|"NEUTRAL"|"NEGATIVE", "score": float}.

        Raises an ExternalAnalysisServiceError subclass; its error_code decides FAILED or retry.
        """


class UnknownAnalyzer:
    """Stands in for an unknown SENTIMENT_ANALYZER value; fails only when used."""

    model_id = ""

    def __init__(self, name):
        self.name = name

    def analyze_sentiment(self, text):
        raise AnalysisConfigError(
            f"SENTIMENT_ANALYZER={self.name!r} is not one of {', '.join(ADAPTERS)}."
        )


def build_analyzer():
    """Return the adapter named by settings.SENTIMENT_ANALYZER; never loads a model."""
    name = settings.SENTIMENT_ANALYZER
    if name == "local":
        return LocalTransformersAnalyzer(
            model_path=settings.SENTIMENT_MODEL_PATH,
            model_id=settings.SENTIMENT_MODEL_ID,
            weights_sha256=settings.SENTIMENT_MODEL_SHA256,
        )
    if name == "huggingface":
        return HuggingFaceClient()
    return UnknownAnalyzer(name)
