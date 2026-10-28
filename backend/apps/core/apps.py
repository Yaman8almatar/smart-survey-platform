from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configures the core Django app that owns domain models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
