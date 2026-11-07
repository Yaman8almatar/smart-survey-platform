# FR-02 (TASK-16), step 2 of 3: data only. Maps free-text regions and interests to the
# fixed D-108 codes. The maps are frozen here on purpose: a migration must not depend on
# enums that may change later.

import re

from django.db import migrations

GOVERNORATE_LABELS = {
    "ALEPPO": "Aleppo",
    "AL_HASAKAH": "Al-Hasakah",
    "AS_SUWAYDA": "As-Suwayda",
    "DAMASCUS": "Damascus",
    "DARAA": "Daraa",
    "DEIR_EZ_ZOR": "Deir ez-Zor",
    "HAMA": "Hama",
    "HOMS": "Homs",
    "IDLIB": "Idlib",
    "LATAKIA": "Latakia",
    "QUNEITRA": "Quneitra",
    "RAQQA": "Raqqa",
    "RIF_DIMASHQ": "Rif Dimashq",
    "TARTUS": "Tartus",
    "OUTSIDE_SYRIA": "Outside Syria",
}

INTEREST_LABELS = {
    "TECHNOLOGY": "Technology",
    "EDUCATION": "Education",
    "HEALTH": "Health",
    "SPORTS": "Sports",
    "FOOD": "Food and cooking",
    "TRAVEL": "Travel",
    "SHOPPING": "Shopping",
    "FINANCE": "Money and finance",
    "CAREERS": "Jobs and careers",
    "ARTS": "Arts and culture",
    "ENTERTAINMENT": "Entertainment",
    "ENVIRONMENT": "Environment",
}

# Extra spellings per code; the code itself and its English label are added below.
REGION_EXTRA_ALIASES = {
    "ALEPPO": ["Halab", "حلب"],
    "AL_HASAKAH": ["Hasakah", "Hassakeh", "Al Hasakah", "Hasaka", "الحسكة", "الحسكه"],
    "AS_SUWAYDA": ["Sweida", "Suwayda", "Suwaida", "السويداء"],
    "DAMASCUS": ["Dimashq", "دمشق"],
    "DARAA": ["Deraa", "Dara'a", "درعا"],
    "DEIR_EZ_ZOR": ["Deir Ezzor", "Deir al-Zor", "Deir Ez Zor", "Deir Alzour", "دير الزور"],
    "HAMA": ["Hamah", "حماة", "حماه"],
    "HOMS": ["حمص"],
    "IDLIB": ["Idleb", "إدلب", "ادلب"],
    "LATAKIA": ["Lattakia", "Latakiya", "اللاذقية", "اللاذقيه"],
    "QUNEITRA": ["Qunaitra", "القنيطرة", "القنيطره"],
    "RAQQA": ["Raqqah", "Ar-Raqqah", "Ar-Raqqa", "الرقة", "الرقه"],
    "RIF_DIMASHQ": [
        "Damascus Countryside",
        "Rural Damascus",
        "Rif Damascus",
        "ريف دمشق",
    ],
    "TARTUS": ["Tartous", "Tartus", "طرطوس"],
    "OUTSIDE_SYRIA": [],
}

INTEREST_KEYWORDS = {
    "technology": "TECHNOLOGY",
    "tech": "TECHNOLOGY",
    "education": "EDUCATION",
    "learning": "EDUCATION",
    "health": "HEALTH",
    "sport": "SPORTS",
    "sports": "SPORTS",
    "food": "FOOD",
    "cooking": "FOOD",
    "travel": "TRAVEL",
    "shopping": "SHOPPING",
    "money": "FINANCE",
    "finance": "FINANCE",
    "banking": "FINANCE",
    "job": "CAREERS",
    "jobs": "CAREERS",
    "career": "CAREERS",
    "careers": "CAREERS",
    "art": "ARTS",
    "arts": "ARTS",
    "culture": "ARTS",
    "entertainment": "ENTERTAINMENT",
    "music": "ENTERTAINMENT",
    "movies": "ENTERTAINMENT",
    "environment": "ENVIRONMENT",
}

_REMOVED_CHARACTERS = re.compile(r"[\s\-'’]")
_LETTER_RUNS = re.compile(r"[^\W\d_]+")


def normalise(text):
    """Casefold and drop spaces, hyphens and apostrophes so spellings compare equal."""
    return _REMOVED_CHARACTERS.sub("", (text or "").casefold())


def _build_region_aliases():
    aliases = {}
    for code, label in GOVERNORATE_LABELS.items():
        for alias in [code, label, *REGION_EXTRA_ALIASES[code]]:
            aliases[normalise(alias)] = code
    return aliases


REGION_ALIASES = _build_region_aliases()


def map_region(text):
    """Return the governorate code for a free-text region, or None when unknown."""
    return REGION_ALIASES.get(normalise(text))


def map_interests(text):
    """Return interest codes found in free text, in first-seen order, unknown words dropped."""
    codes = []
    for word in _LETTER_RUNS.findall(text or ""):
        code = INTEREST_KEYWORDS.get(word.casefold())
        if code and code not in codes:
            codes.append(code)
    return codes


def forward(apps, schema_editor):
    RespondentProfile = apps.get_model("core", "RespondentProfile")
    TargetingCriteria = apps.get_model("core", "TargetingCriteria")

    unmapped_profiles = 0
    for profile in RespondentProfile.objects.all():
        code = map_region(profile.region)
        if code is None:
            unmapped_profiles += 1
        profile.region = code or ""
        profile.interests_codes = map_interests(profile.interests)
        profile.save(update_fields=["region", "interests_codes"])

    unmapped_criteria = 0
    for criteria in TargetingCriteria.objects.exclude(region__isnull=True).exclude(region=""):
        code = map_region(criteria.region)
        if code is None:
            unmapped_criteria += 1
        criteria.region = code
        criteria.save(update_fields=["region"])

    print(
        f"\n  FR-02 region mapping: {unmapped_profiles} profile region(s) not mapped (set to \"\"), "
        f"{unmapped_criteria} targeting region(s) not mapped (set to NULL)."
    )


def reverse(apps, schema_editor):
    RespondentProfile = apps.get_model("core", "RespondentProfile")
    TargetingCriteria = apps.get_model("core", "TargetingCriteria")

    for profile in RespondentProfile.objects.all():
        profile.region = GOVERNORATE_LABELS.get(profile.region, profile.region)
        profile.interests = ", ".join(
            INTEREST_LABELS.get(code, code) for code in profile.interests_codes
        )
        profile.save(update_fields=["region", "interests"])

    for criteria in TargetingCriteria.objects.exclude(region__isnull=True).exclude(region=""):
        criteria.region = GOVERNORATE_LABELS.get(criteria.region, criteria.region)
        criteria.save(update_fields=["region"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_profile_optional_fields"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
