# FR-02 (TASK-16), step 1 of 3: schema only, no row updates in this transaction.

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_performance_indexes_and_constraints"),
    ]

    operations = [
        migrations.AddField(
            model_name="respondentprofile",
            name="education",
            field=models.CharField(
                blank=True,
                choices=[
                    ("BASIC", "Basic education or less"),
                    ("SECONDARY", "Secondary school"),
                    ("INSTITUTE", "Institute diploma"),
                    ("BACHELOR", "Bachelor's degree"),
                    ("MASTER", "Master's degree"),
                    ("DOCTORATE", "Doctorate"),
                    ("PREFER_NOT_TO_SAY", "Prefer not to say"),
                ],
                default="",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="respondentprofile",
            name="occupation",
            field=models.CharField(
                blank=True,
                choices=[
                    ("STUDENT", "Student"),
                    ("PUBLIC_SECTOR", "Public sector employee"),
                    ("PRIVATE_SECTOR", "Private sector employee"),
                    ("SELF_EMPLOYED", "Self-employed or business owner"),
                    ("LOOKING_FOR_WORK", "Looking for work"),
                    ("HOMEMAKER", "Homemaker"),
                    ("RETIRED", "Retired"),
                    ("OTHER", "Other"),
                    ("PREFER_NOT_TO_SAY", "Prefer not to say"),
                ],
                default="",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="respondentprofile",
            name="marital_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SINGLE", "Single"),
                    ("MARRIED", "Married"),
                    ("DIVORCED", "Divorced"),
                    ("WIDOWED", "Widowed"),
                    ("PREFER_NOT_TO_SAY", "Prefer not to say"),
                ],
                default="",
                max_length=32,
            ),
        ),
        # Temporary column filled by 0004 and renamed to "interests" by 0005.
        migrations.AddField(
            model_name="respondentprofile",
            name="interests_codes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=32),
                default=list,
                size=None,
            ),
        ),
        # A default lets the reverse of 0005 re-add the old text column on a table with rows.
        migrations.AlterField(
            model_name="respondentprofile",
            name="interests",
            field=models.TextField(blank=True, default=""),
        ),
    ]
