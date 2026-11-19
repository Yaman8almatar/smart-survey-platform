from django.db import models
from django.db.models import Value


class ResponseQuality(models.Model):
    """FR-04 evidence stored with one response at submit; facts only, no flag or score (P-01)."""

    quality_id = models.BigAutoField(primary_key=True)
    response = models.OneToOneField(
        "core.Response",
        on_delete=models.CASCADE,
        related_name="quality",
    )
    # Copied from the response so the same-device comparison has an index.
    survey = models.ForeignKey(
        "core.Survey",
        on_delete=models.CASCADE,
        related_name="+",
    )
    timings = models.JSONField(default=list, db_default=Value([], output_field=models.JSONField()))
    active_ms = models.BigIntegerField(null=True, blank=True)
    attention_total = models.PositiveSmallIntegerField(default=0, db_default=0)
    attention_failed = models.PositiveSmallIntegerField(default=0, db_default=0)
    rating_count = models.PositiveSmallIntegerField(default=0, db_default=0)
    rating_all_same = models.BooleanField(default=False, db_default=False)
    # Hex HMAC-SHA256 of the app's device id with DEVICE_HASH_KEY; the raw id is never stored.
    device_hash = models.CharField(max_length=64, blank=True, default="", db_default="")
    signals_ok = models.BooleanField()

    class Meta:
        db_table = "response_quality"
        indexes = [
            models.Index(fields=["survey", "device_hash"], name="resp_quality_device_idx"),
        ]

    def __str__(self):
        """Return a readable quality label."""
        return f"Quality of response {self.response_id}"
