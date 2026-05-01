import os

import requests

from core.exceptions import ExternalAnalysisServiceError


class HuggingFaceClient:
    """Isolates external Hugging Face sentiment API communication."""

    LABEL_MAP = {
        "POSITIVE": "POSITIVE",
        "LABEL_2": "POSITIVE",
        "2": "POSITIVE",
        "NEGATIVE": "NEGATIVE",
        "LABEL_0": "NEGATIVE",
        "0": "NEGATIVE",
        "NEUTRAL": "NEUTRAL",
        "LABEL_1": "NEUTRAL",
        "1": "NEUTRAL",
    }

    def __init__(self, api_token=None, model_url=None, timeout=15):
        """Configure Hugging Face credentials, model endpoint, and timeout."""
        self.api_token = self._clean_value(
            api_token if api_token is not None else os.getenv("HF_API_TOKEN")
        )
        self.model_url = self._clean_value(
            model_url if model_url is not None else os.getenv("HF_SENTIMENT_MODEL_URL")
        )
        self.timeout = timeout

    def analyze_sentiment(self, text):
        """Send open-text content to Hugging Face and return normalized sentiment output."""
        if not self.api_token:
            raise ExternalAnalysisServiceError("HF_API_TOKEN is not configured.")
        if not self.model_url:
            raise ExternalAnalysisServiceError("HF_SENTIMENT_MODEL_URL is not configured.")
        if not isinstance(text, str) or not text.strip():
            raise ExternalAnalysisServiceError("Input text must not be empty.")

        headers = {"Authorization": f"Bearer {self.api_token}"}
        payload = {"inputs": text}

        try:
            # Send the sentiment analysis request to Hugging Face.
            response = requests.post(
                self.model_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ExternalAnalysisServiceError("Hugging Face request failed.") from exc

        return self._parse_response(response)

    def _clean_value(self, value):
        """Normalize optional configuration values from arguments or environment."""
        if value is None:
            return None
        return str(value).strip()

    def _parse_response(self, response):
        """Parse and normalize the Hugging Face response payload."""
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalAnalysisServiceError("Hugging Face response is invalid.") from exc

        predictions = self._extract_predictions(payload)
        best_prediction = self._best_prediction(predictions)

        return {
            "label": self._normalize_label(best_prediction["label"]),
            "score": self._normalize_score(best_prediction["score"]),
        }

    def _extract_predictions(self, payload):
        """Extract prediction rows from supported Hugging Face response shapes."""
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            predictions = payload[0]
        else:
            predictions = payload

        if not isinstance(predictions, list) or not predictions:
            raise ExternalAnalysisServiceError("Hugging Face response is invalid.")

        for prediction in predictions:
            if not isinstance(prediction, dict):
                raise ExternalAnalysisServiceError("Hugging Face response is invalid.")
            if "label" not in prediction or "score" not in prediction:
                raise ExternalAnalysisServiceError("Hugging Face response is invalid.")
            self._normalize_label(prediction["label"])
            self._normalize_score(prediction["score"])

        return predictions

    def _best_prediction(self, predictions):
        """Return the highest-confidence sentiment prediction."""
        return max(
            predictions,
            key=lambda prediction: self._normalize_score(prediction["score"]),
        )

    def _normalize_label(self, label):
        """Normalize external sentiment labels into internal sentiment categories."""
        normalized_label = str(label).strip().upper()
        # Normalize provider labels into the internal sentiment labels.
        mapped_label = self.LABEL_MAP.get(normalized_label)
        if mapped_label is None:
            raise ExternalAnalysisServiceError("Unknown sentiment label.")
        return mapped_label

    def _normalize_score(self, score):
        """Normalize the external confidence score to a float."""
        try:
            return float(score)
        except (TypeError, ValueError) as exc:
            raise ExternalAnalysisServiceError("Hugging Face response is invalid.") from exc
