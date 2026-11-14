import importlib

import pytest

from core.enums import Governorate, Interest

# Migration module names start with a digit, so they can only be imported with importlib.
migration = importlib.import_module("apps.core.migrations.0004_map_profile_lists")


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Damascus", "DAMASCUS"),
        ("  aleppo ", "ALEPPO"),
        ("Deir ez-Zor", "DEIR_EZ_ZOR"),
        ("Rif Dimashq", "RIF_DIMASHQ"),
        ("RIF_DIMASHQ", "RIF_DIMASHQ"),
        ("Outside Syria", "OUTSIDE_SYRIA"),
        ("دمشق", "DAMASCUS"),
        ("دير الزور", "DEIR_EZ_ZOR"),
        ("ريف دمشق", "RIF_DIMASHQ"),
        ("إدلب", "IDLIB"),
        ("Lattakia", "LATAKIA"),
        ("Hassakeh", "AL_HASAKAH"),
        ("Deir al-Zor", "DEIR_EZ_ZOR"),
        ("Dara'a", "DARAA"),
        ("Rural Damascus", "RIF_DIMASHQ"),
        ("Ar-Raqqah", "RAQQA"),
        ("Tartous", "TARTUS"),
    ],
)
def test_map_region_maps_english_arabic_and_misspelled_names(text, code):
    assert migration.map_region(text) == code


@pytest.mark.parametrize("text", ["Amman", "", None, "Damascus City"])
def test_map_region_returns_none_for_unknown_values(text):
    assert migration.map_region(text) is None


def test_every_governorate_code_and_label_is_an_alias():
    for code, label in Governorate.choices:
        assert migration.map_region(code) == code
        assert migration.map_region(label) == code


def test_migration_labels_match_the_enums():
    assert migration.GOVERNORATE_LABELS == dict(Governorate.choices)
    assert migration.INTEREST_LABELS == dict(Interest.choices)


@pytest.mark.parametrize(
    ("text", "codes"),
    [
        ("Technology, sports", ["TECHNOLOGY", "SPORTS"]),
        ("music & movies; travel", ["ENTERTAINMENT", "TRAVEL"]),
        ("Jobs/careers, banking and money", ["CAREERS", "FINANCE"]),
        ("tech-learning", ["TECHNOLOGY", "EDUCATION"]),
        ("ART, culture, Health", ["ARTS", "HEALTH"]),
        ("customer experience, digital services", []),
        ("", []),
        (None, []),
    ],
)
def test_map_interests_keeps_first_seen_order_and_drops_unknown_words(text, codes):
    assert migration.map_interests(text) == codes
