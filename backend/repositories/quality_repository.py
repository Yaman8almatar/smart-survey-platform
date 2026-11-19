from apps.core.models import ResponseQuality


class QualityRepository:
    """Provides database access for the FR-04 evidence of responses."""

    def save(self, quality):
        """Persist the evidence row of one response."""
        quality.save()
        return quality
