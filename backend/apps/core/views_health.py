from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from services.health_service import HealthService


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
    if HealthService().is_database_ready():
        return JsonResponse({"status": "ready", "database": "connected"})
    return JsonResponse({"status": "not_ready", "database": "disconnected"}, status=503)
