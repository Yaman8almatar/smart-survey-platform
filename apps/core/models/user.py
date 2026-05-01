from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.enums import AccountStatus, UserType


class UserManager(BaseUserManager):
    """Creates email-based users for Django authentication."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular email-based user account."""
        if not email:
            raise ValueError("The email field must be set.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an administrator account for Django admin access."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", UserType.ADMIN)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Represents a platform account with role and account status."""

    user_id = models.BigAutoField(primary_key=True)
    username = None
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=32, choices=UserType.choices)
    account_status = models.CharField(
        max_length=32,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        """Return the email used to identify the account."""
        return self.email

    def activate(self):
        """Mark the account as active."""
        self.account_status = AccountStatus.ACTIVE

    def suspend(self):
        """Mark the account as suspended."""
        self.account_status = AccountStatus.SUSPENDED

    def mark_deleted(self):
        """Soft-delete the account by changing its status."""
        self.account_status = AccountStatus.DELETED
