# FR-03 (TASK-33), step 2 of 3: data only. Copies the single targeting region into the
# new regions list.

from django.db import migrations


def forward(apps, schema_editor):
    TargetingCriteria = apps.get_model("core", "TargetingCriteria")
    for criteria in TargetingCriteria.objects.all():
        criteria.regions = [criteria.region] if criteria.region else []
        criteria.save(update_fields=["regions"])


def reverse(apps, schema_editor):
    # Lossy on purpose: the old column holds one governorate, so a list with more than one
    # value keeps only its first. The database backup taken before TASK-33 is the full way back.
    TargetingCriteria = apps.get_model("core", "TargetingCriteria")
    for criteria in TargetingCriteria.objects.all():
        criteria.region = criteria.regions[0] if criteria.regions else None
        criteria.save(update_fields=["region"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_targeting_lists_add"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
