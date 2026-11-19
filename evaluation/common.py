"""Shared paths, script ranges, normalisations and label maps (PROTOCOL.md sections 3, 4 and 6)."""

import hashlib
import re
import unicodedata
from pathlib import Path

T2 = Path(r"C:\t2")
RAW = T2 / "data" / "raw"
DATA = T2 / "data"
MODELS = T2 / "models"
AUDIT = T2 / "audit"
EVAL = Path(__file__).resolve().parent
RESULTS = EVAL / "results"

SEED = 20261118
LABELS = ("negative", "neutral", "positive")

# Same ranges as backend/services/text_language.py.
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


def in_ranges(char, ranges):
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in ranges)


def letters(text):
    return [char for char in text if unicodedata.category(char).startswith("L")]


def script_share(text, ranges):
    """Share of the letters of text that fall in ranges (0.0 when there is no letter)."""
    found = letters(text)
    if not found:
        return 0.0
    return sum(1 for char in found if in_ranges(char, ranges)) / len(found)


def routes_to_arabic(text):
    """The backend's language rule: Arabic when Arabic letters are at least half of the letters."""
    found = letters(text)
    if not found:
        return False
    return sum(1 for char in found if in_ranges(char, ARABIC_RANGES)) * 2 >= len(found)


URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@\w+")
ARABIC_MARKS = {chr(c) for c in range(0x064B, 0x0653)} | {"\u0670", "\u0640"}
SPACE_RE = re.compile(r"\s+")


def normalise_a(text):
    text = unicodedata.normalize("NFKC", text)
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = "".join(char for char in text if char not in ARABIC_MARKS)
    text = "".join(char.lower() if in_ranges(char, LATIN_RANGES) else char for char in text)
    return SPACE_RE.sub(" ", text).strip()


def normalise_b(text):
    text = normalise_a(text)
    text = "".join(
        " " if unicodedata.category(char)[0] in "PS" or unicodedata.category(char) == "Nd" else char
        for char in text
    )
    return SPACE_RE.sub(" ", text).strip()


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def overlap_hashes(text):
    """The A-hash and, when the B-text is not empty, the B-hash of text."""
    hashes = {sha256(normalise_a(text))}
    b_text = normalise_b(text)
    if b_text:
        hashes.add(sha256(b_text))
    return hashes
