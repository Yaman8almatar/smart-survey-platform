from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.core.models import User


class UserRepository:
    """Provides database access for user accounts and account report metrics."""

    def save(self, user):
        """Persist a user account."""
        user.save()
        return user

    def find_by_id(self, user_id):
        """Return a user account by its primary key."""
        return User.objects.filter(user_id=user_id).first()

    def find_by_email(self, email):
        """Return a user account by email address."""
        return User.objects.filter(email=email).first()

    def email_exists(self, email):
        """Return whether an email is already registered."""
        return User.objects.filter(email=email).exists()

    def save(self, user):
        """Persist a user account."""
        user.save()
        return user

    def delete(self, user):
        """Delete a user account record."""
        user.delete()

    def update(self, user):
        """Persist changes to a user account."""
        user.save()
        return user

    def list_all(self):
        """Return all user accounts for admin review."""
        return User.objects.all()

    def count_by_user_type(self):
        """Return user counts grouped by platform role."""
        return (
            User.objects.values("user_type")
            .annotate(count=Count("user_id"))
            .order_by("user_type")
        )

    def count_created_by_date(self, date_from, date_to):
        """Return new user counts grouped by creation date."""
        return (
            User.objects.filter(
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            )
            .annotate(created_date=TruncDate("created_at"))
            .values("created_date")
            .annotate(count=Count("user_id"))
            .order_by("created_date")
        )
