from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.models import SentimentAnalysisResult, TargetingCriteria
from core.enums import AnalysisStatus, Governorate


@pytest.mark.django_db
def test_seed_targets_the_demo_survey_at_one_governorate_list():
    call_command("seed_demo_data", stdout=StringIO())

    [criteria] = TargetingCriteria.objects.all()
    assert criteria.regions == [Governorate.DAMASCUS]


@pytest.mark.django_db
def test_seed_writes_the_demo_sentiment_result_as_pending():
    call_command("seed_demo_data", stdout=StringIO())

    [result] = SentimentAnalysisResult.objects.all()
    assert result.status == AnalysisStatus.PENDING
    assert result.sentiment_label is None
    assert result.sentiment_score is None
    assert result.analyzed_at is None
    assert result.attempts == 0


@pytest.mark.django_db
def test_seed_resets_an_existing_completed_result_to_pending():
    call_command("seed_demo_data", stdout=StringIO())
    SentimentAnalysisResult.objects.update(
        status=AnalysisStatus.COMPLETED, sentiment_label="POSITIVE", sentiment_score=0.95
    )

    call_command("seed_demo_data", stdout=StringIO())

    [result] = SentimentAnalysisResult.objects.all()
    assert result.status == AnalysisStatus.PENDING
    assert result.sentiment_label is None
    assert result.sentiment_score is None
