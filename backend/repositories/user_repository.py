from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.core.models import User


class UserRepository:
    """Provides database access for user accounts and account report metrics."""

    def find_by_id(self, user_id):
        """Return a user account by its primary key."""
        return User.objects.filter(user_id=user_id).first()

    def find_by_email(self, email):
        """Return a user account by email address (case-insensitive)."""
        if not email:
            return None
        return User.objects.filter(email__iexact=email.strip()).first()

    def email_exists(self, email):
        """Return whether an email is already registered (case-insensitive)."""
        if not email:
            return False
        return User.objects.filter(email__iexact=email.strip()).exists()

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
        import datetime
        from django.utils import timezone

        if isinstance(date_from, datetime.date) and not isinstance(date_from, datetime.datetime):
            start_dt = timezone.make_aware(datetime.datetime.combine(date_from, datetime.time.min))
        else:
            start_dt = date_from

        if isinstance(date_to, datetime.date) and not isinstance(date_to, datetime.datetime):
            end_dt = timezone.make_aware(datetime.datetime.combine(date_to, datetime.time.max))
        else:
            end_dt = date_to

        return (
            User.objects.filter(
                created_at__range=(start_dt, end_dt),
            )
            .annotate(created_date=TruncDate("created_at"))
            .values("created_date")
            .annotate(count=Count("user_id"))
            .order_by("created_date")
        )
