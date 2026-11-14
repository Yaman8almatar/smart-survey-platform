import logging
from celery import shared_task
from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)


# Dormant (Q4): nothing dispatches this task; run_analysis_worker does the work.
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.core.tasks.analyze_open_text_answers_task",
)
def analyze_open_text_answers_task(self, response_id):
    """Run one analysis worker batch; response_id is only logged."""
    logger.info("Celery analysis task runs one worker batch (response_id=%s).", response_id)
    return [result.result_id for result in AnalysisService().process_pending_batch()]
