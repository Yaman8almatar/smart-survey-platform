from apps.core.models import SentimentAnalysisResult


class AnalysisRepository:
    """Provides database access for sentiment analysis results."""

    def save(self, result):
        """Persist a sentiment analysis result."""
        result.save()
        return result

    def find_by_answer_id(self, answer_id):
        """Return the sentiment result for one answer."""
        return SentimentAnalysisResult.objects.filter(answer_id=answer_id).first()

    def find_by_survey_id(self, survey_id):
        """Return sentiment results produced by answers for a survey."""
        return SentimentAnalysisResult.objects.filter(
            answer__response__survey_id=survey_id
        ).select_related("answer", "answer__response", "answer__response__survey")

    def update(self, result):
        """Persist changes to a sentiment analysis result."""
        result.save()
        return result
