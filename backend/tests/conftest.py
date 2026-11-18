import pytest


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):
    """Tests only: a fast hasher, because PBKDF2 at 1,000,000 iterations dominates test time (D-169)."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
