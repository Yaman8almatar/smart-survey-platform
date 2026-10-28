import logging
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def liveness_probe(request):
    """Kubernetes / Docker liveness probe: returns 200 if process is running."""
    return JsonResponse({"status": "live", "uptime": "ok"})


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_probe(request):
    """Kubernetes / Docker readiness probe: verifies database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ready", "database": "connected"})
    except Exception as exc:
        logger.error("Readiness probe database check failed: %s", exc)
        return JsonResponse(
            {"status": "not_ready", "database": "disconnected", "error": str(exc)},
            status=503,
        )
