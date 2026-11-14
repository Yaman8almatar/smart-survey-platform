# FR-02 (TASK-16), step 3 of 3: schema only. Swaps in the mapped interests column and
# narrows both region columns to the governorate codes.

import django.contrib.postgres.fields
from django.db import migrations, models

GOVERNORATE_CHOICES = [
    ("ALEPPO", "Aleppo"),
    ("AL_HASAKAH", "Al-Hasakah"),
    ("AS_SUWAYDA", "As-Suwayda"),
    ("DAMASCUS", "Damascus"),
    ("DARAA", "Daraa"),
    ("DEIR_EZ_ZOR", "Deir ez-Zor"),
    ("HAMA", "Hama"),
    ("HOMS", "Homs"),
    ("IDLIB", "Idlib"),
    ("LATAKIA", "Latakia"),
    ("QUNEITRA", "Quneitra"),
    ("RAQQA", "Raqqa"),
    ("RIF_DIMASHQ", "Rif Dimashq"),
    ("TARTUS", "Tartus"),
    ("OUTSIDE_SYRIA", "Outside Syria"),
]

INTEREST_CHOICES = [
    ("TECHNOLOGY", "Technology"),
    ("EDUCATION", "Education"),
    ("HEALTH", "Health"),
    ("SPORTS", "Sports"),
    ("FOOD", "Food and cooking"),
    ("TRAVEL", "Travel"),
    ("SHOPPING", "Shopping"),
    ("FINANCE", "Money and finance"),
    ("CAREERS", "Jobs and careers"),
    ("ARTS", "Arts and culture"),
    ("ENTERTAINMENT", "Entertainment"),
    ("ENVIRONMENT", "Environment"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_map_profile_lists"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="respondentprofile",
            name="interests",
        ),
        migrations.RenameField(
            model_name="respondentprofile",
            old_name="interests_codes",
            new_name="interests",
        ),
        migrations.AlterField(
            model_name="respondentprofile",
            name="interests",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(choices=INTEREST_CHOICES, max_length=32),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="respondentprofile",
            name="region",
            field=models.CharField(blank=True, choices=GOVERNORATE_CHOICES, max_length=32),
        ),
        migrations.AlterField(
            model_name="targetingcriteria",
            name="region",
            field=models.CharField(
                blank=True,
                choices=GOVERNORATE_CHOICES,
                max_length=32,
                null=True,
            ),
        ),
    ]
