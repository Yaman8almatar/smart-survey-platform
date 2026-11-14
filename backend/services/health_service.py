import logging

from repositories.health_repository import HealthRepository

logger = logging.getLogger(__name__)


class HealthService:
    """Answers the health probes without exposing failure details to clients."""

    def __init__(self, health_repository=None):
        """Wire the repository used for the database check."""
        self.health_repository = health_repository or HealthRepository()

    def is_database_ready(self):
        """Return whether the database answers; log the failure and return False otherwise."""
        try:
            self.health_repository.ping()
        except Exception:
            logger.exception("Readiness probe database check failed.")
            return False
        return True
