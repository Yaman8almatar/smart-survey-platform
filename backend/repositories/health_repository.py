from django.db import connection


class HealthRepository:
    """Provides the database round trip used by the readiness probe."""

    def ping(self):
        """Run SELECT 1 on the default database; raise if it cannot answer."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
