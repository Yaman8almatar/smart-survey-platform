"""Guess the language of an answer from the script of its letters."""

import unicodedata

ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
LATIN_RANGES = (
    (0x0041, 0x005A),
    (0x0061, 0x007A),
    (0x00C0, 0x024F),
)


def detect_language(text):
    """Return "ar", "en", "other", or None when the text has no letter."""
    letters = [char for char in text or "" if unicodedata.category(char).startswith("L")]
    if not letters:
        return None

    arabic_count = sum(1 for char in letters if _in_ranges(char, ARABIC_RANGES))
    if arabic_count * 2 >= len(letters):
        return "ar"

    latin_count = sum(1 for char in letters if _in_ranges(char, LATIN_RANGES))
    if latin_count * 2 >= len(letters):
        return "en"

    return "other"


def _in_ranges(char, ranges):
    """Return whether the character's code point falls in one of the ranges."""
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in ranges)
