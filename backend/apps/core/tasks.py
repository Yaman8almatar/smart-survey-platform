import logging
from celery import shared_task
from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.core.tasks.analyze_open_text_answers_task",
)
def analyze_open_text_answers_task(self, response_id):
    """Run sentiment analysis on open-text answers asynchronously in worker thread."""
    logger.info("Executing asynchronous sentiment analysis for response_id=%s", response_id)
    try:
        service = AnalysisService()
        return [
            result.result_id
            for result in service.analyze_open_text_answers(response_id)
        ]
    except Exception as exc:
        logger.error(
            "Sentiment analysis task failed for response_id=%s: %s. Retrying...",
            response_id,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)
