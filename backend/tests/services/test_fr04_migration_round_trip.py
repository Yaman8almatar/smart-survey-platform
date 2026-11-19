"""FR-04 (TASK-41): 0012 and 0013 apply and reverse; inserts that name no new column still work."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.core.models import Survey, User
from core.enums import UserType

BEFORE = [("core", "0011_survey_reach_at_publish")]
AFTER = [("core", "0013_fr04_snapshot_fill")]


def migrate_to(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True)
def test_0013_fills_the_snapshot_and_both_migrations_reverse():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes("core")
    old_apps = migrate_to(BEFORE)
    try:
        User = old_apps.get_model("core", "User")
        Survey = old_apps.get_model("core", "Survey")
        Profile = old_apps.get_model("core", "RespondentProfile")
        Response = old_apps.get_model("core", "Response")

        provider = User.objects.create(
            email="fr04-round-trip-provider@example.com",
            name="Provider",
            user_type="SERVICE_PROVIDER",
        )
        respondent = User.objects.create(
            email="fr04-round-trip-respondent@example.com",
            name="Respondent",
            user_type="RESPONDENT",
        )
        Profile.objects.create(
            user=respondent,
            age=41,
            gender="FEMALE",
            region="HOMS",
            interests=["HEALTH", "ARTS"],
            education="MASTER",
            occupation="RETIRED",
            marital_status="MARRIED",
        )
        survey = Survey.objects.create(provider=provider, title="Before FR-04")
        response = Response.objects.create(survey=survey, respondent=respondent)

        new_apps = migrate_to(AFTER)
        stored = new_apps.get_model("core", "Response").objects.get(pk=response.pk)
        assert stored.snap_age == 41
        assert stored.snap_gender == "FEMALE"
        assert stored.snap_region == "HOMS"
        assert stored.snap_education == "MASTER"
        assert stored.snap_occupation == "RETIRED"
        assert stored.snap_marital_status == "MARRIED"
        assert stored.snap_interests == ["HEALTH", "ARTS"]
        assert stored.is_excluded is False
        assert new_apps.get_model("core", "Question")._meta.get_field("is_attention_check")

        old_apps = migrate_to(BEFORE)
        Response = old_apps.get_model("core", "Response")
        assert Response.objects.filter(pk=response.pk).exists()
        with connection.cursor() as cursor:
            columns = [
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, "responses"
                )
            ]
            tables = connection.introspection.table_names(cursor)
        assert not any(name.startswith("snap_") for name in columns)
        assert "response_quality" not in tables
    finally:
        migrate_to(latest)


@pytest.mark.django_db
def test_raw_inserts_that_name_no_new_column_succeed():
    provider = User.objects.create_user(
        email="fr04-raw-provider@example.com",
        password="strong-password",
        name="Provider",
        user_type=UserType.SERVICE_PROVIDER,
    )
    respondent = User.objects.create_user(
        email="fr04-raw-respondent@example.com",
        password="strong-password",
        name="Respondent",
        user_type=UserType.RESPONDENT,
    )
    survey = Survey.objects.create(provider=provider, title="Raw insert")

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO questions (survey_id, question_text, question_type, is_required,"
            " order_index) VALUES (%s, 'Raw', 'OPEN_TEXT', true, 0)"
            " RETURNING is_attention_check, expected_option_id, expected_rating",
            [survey.survey_id],
        )
        question_row = cursor.fetchone()
        cursor.execute(
            "INSERT INTO responses (survey_id, respondent_id, submitted_at)"
            " VALUES (%s, %s, %s)"
            " RETURNING is_excluded, excluded_at, snap_age, snap_gender, snap_interests",
            [survey.survey_id, respondent.user_id, timezone.now()],
        )
        response_row = cursor.fetchone()

    assert question_row == (False, None, None)
    assert response_row == (False, None, None, "", [])
