from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Configures the versioned REST API presentation app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
