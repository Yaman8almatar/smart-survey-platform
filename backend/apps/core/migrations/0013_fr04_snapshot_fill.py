# FR-04 (TASK-41), data only. Fills the profile snapshot of every existing response from its
# respondent's current profile. Every response before TASK-41 is demo data, so the current
# profile stands in for the one at submit; from TASK-41 on, submit_response writes the snapshot.

from django.db import migrations


def forward(apps, schema_editor):
    Response = apps.get_model("core", "Response")
    RespondentProfile = apps.get_model("core", "RespondentProfile")
    profiles = {profile.user_id: profile for profile in RespondentProfile.objects.all()}
    for response in Response.objects.all():
        profile = profiles.get(response.respondent_id)
        if profile is None:
            continue
        response.snap_age = profile.age
        response.snap_gender = profile.gender
        response.snap_region = profile.region
        response.snap_education = profile.education
        response.snap_occupation = profile.occupation
        response.snap_marital_status = profile.marital_status
        response.snap_interests = list(profile.interests)
        response.save(
            update_fields=[
                "snap_age",
                "snap_gender",
                "snap_region",
                "snap_education",
                "snap_occupation",
                "snap_marital_status",
                "snap_interests",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_fr04_evidence_fields"),
    ]

    operations = [
        # Reverse is a no-op: 0012's reverse drops the snapshot columns.
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
