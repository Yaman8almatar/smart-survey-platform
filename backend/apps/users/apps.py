from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configures the users presentation app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
