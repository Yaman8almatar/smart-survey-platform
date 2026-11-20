import datetime

import pytest
from django.utils import timezone

from apps.core.models import Survey

ELIGIBLE_URL = "/api/v1/surveys/eligible/"

pytestmark = pytest.mark.django_db


def test_eligible_row_has_the_fr08_keys_and_types(client, authenticate, respondent, survey):
    published_at = timezone.now() - datetime.timedelta(days=1)
    Survey.objects.filter(pk=survey.pk).update(published_at=published_at)
    authenticate(respondent)

    (row,) = client.get(ELIGIBLE_URL).json()

    assert set(row) == {
        "id",
        "title",
        "description",
        "question_count",
        "expected_minutes",
        "published_on",
    }
    assert isinstance(row["expected_minutes"], int)
    assert row["published_on"] == timezone.localdate(published_at).isoformat()


def test_eligible_row_published_on_is_null_without_a_publish_time(
    client, authenticate, respondent, survey
):
    authenticate(respondent)

    (row,) = client.get(ELIGIBLE_URL).json()

    assert row["published_on"] is None
