import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def import_settings(**env_overrides):
    """Import config.settings in a fresh interpreter with the given environment values."""
    env = {**os.environ, **env_overrides}
    return subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_missing_secret_key_fails_startup_when_debug_is_false():
    result = import_settings(SECRET_KEY="", DEBUG="False")

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


def test_missing_secret_key_is_allowed_when_debug_is_true():
    result = import_settings(SECRET_KEY="", DEBUG="True")

    assert result.returncode == 0, result.stderr


def test_configured_secret_key_starts_when_debug_is_false():
    result = import_settings(SECRET_KEY="configured-secret-key", DEBUG="False")

    assert result.returncode == 0, result.stderr
