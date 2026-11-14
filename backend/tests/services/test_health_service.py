import logging

import pytest

from services.health_service import HealthService


class FailingHealthRepository:
    def ping(self):
        raise RuntimeError("password=secret host=db")


@pytest.mark.django_db
def test_database_is_ready_when_ping_succeeds():
    assert HealthService().is_database_ready() is True


def test_database_is_not_ready_when_ping_fails_and_error_is_logged(caplog):
    service = HealthService(health_repository=FailingHealthRepository())

    with caplog.at_level(logging.ERROR, logger="services.health_service"):
        ready = service.is_database_ready()

    assert ready is False
    assert "Readiness probe database check failed." in caplog.text
