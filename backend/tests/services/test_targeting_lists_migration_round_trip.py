import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = [("core", "0007_sentiment_worker_fields")]
AFTER = [("core", "0010_targeting_region_remove")]


def migrate_to(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True)
def test_0009_copies_region_into_regions_and_back_on_reverse():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes("core")
    old_apps = migrate_to(BEFORE)
    try:
        User = old_apps.get_model("core", "User")
        Survey = old_apps.get_model("core", "Survey")
        Criteria = old_apps.get_model("core", "TargetingCriteria")

        provider = User.objects.create(
            email="lists-round-trip@example.com", name="Provider", user_type="SERVICE_PROVIDER"
        )
        homs_survey = Survey.objects.create(provider=provider, title="Homs")
        open_survey = Survey.objects.create(provider=provider, title="Open")
        Criteria.objects.create(survey=homs_survey, region="HOMS")
        Criteria.objects.create(survey=open_survey, region=None)

        new_apps = migrate_to(AFTER)
        Criteria = new_apps.get_model("core", "TargetingCriteria")
        assert Criteria.objects.get(survey_id=homs_survey.pk).regions == ["HOMS"]
        assert Criteria.objects.get(survey_id=open_survey.pk).regions == []

        old_apps = migrate_to(BEFORE)
        Criteria = old_apps.get_model("core", "TargetingCriteria")
        assert Criteria.objects.get(survey_id=homs_survey.pk).region == "HOMS"
        assert Criteria.objects.get(survey_id=open_survey.pk).region is None
    finally:
        migrate_to(latest)
