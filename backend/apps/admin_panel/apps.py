from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    """Configures the administrator presentation app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_panel"
