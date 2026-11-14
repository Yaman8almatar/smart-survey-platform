import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = [("core", "0003_profile_optional_fields")]
AFTER = [("core", "0005_profile_lists_final")]


def migrate_to(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True)
def test_0004_maps_rows_forward_and_writes_labels_back_on_reverse():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes("core")
    old_apps = migrate_to(BEFORE)
    try:
        User = old_apps.get_model("core", "User")
        Survey = old_apps.get_model("core", "Survey")
        Profile = old_apps.get_model("core", "RespondentProfile")
        Criteria = old_apps.get_model("core", "TargetingCriteria")

        user = User.objects.create(
            email="round-trip@example.com", name="Round Trip", user_type="RESPONDENT"
        )
        other = User.objects.create(
            email="round-trip-2@example.com", name="Round Trip", user_type="RESPONDENT"
        )
        provider = User.objects.create(
            email="round-trip-provider@example.com",
            name="Provider",
            user_type="SERVICE_PROVIDER",
        )
        Profile.objects.create(
            user=user, age=30, gender="MALE", region="حلب", interests="Tech, music, chess"
        )
        Profile.objects.create(
            user=other, age=40, gender="FEMALE", region="Amman", interests="gardening"
        )
        mapped_survey = Survey.objects.create(provider=provider, title="Mapped")
        unmapped_survey = Survey.objects.create(provider=provider, title="Unmapped")
        Criteria.objects.create(survey=mapped_survey, region="Rural Damascus")
        Criteria.objects.create(survey=unmapped_survey, region="Zarqa")

        new_apps = migrate_to(AFTER)
        Profile = new_apps.get_model("core", "RespondentProfile")
        Criteria = new_apps.get_model("core", "TargetingCriteria")
        mapped = Profile.objects.get(user_id=user.pk)
        assert (mapped.region, mapped.interests) == ("ALEPPO", ["TECHNOLOGY", "ENTERTAINMENT"])
        unmapped = Profile.objects.get(user_id=other.pk)
        assert (unmapped.region, unmapped.interests) == ("", [])
        assert Criteria.objects.get(survey_id=mapped_survey.pk).region == "RIF_DIMASHQ"
        assert Criteria.objects.get(survey_id=unmapped_survey.pk).region is None

        old_apps = migrate_to(BEFORE)
        Profile = old_apps.get_model("core", "RespondentProfile")
        Criteria = old_apps.get_model("core", "TargetingCriteria")
        reversed_profile = Profile.objects.get(user_id=user.pk)
        assert (reversed_profile.region, reversed_profile.interests) == (
            "Aleppo",
            "Technology, Entertainment",
        )
        assert Criteria.objects.get(survey_id=mapped_survey.pk).region == "Rif Dimashq"
    finally:
        migrate_to(latest)
