import pytest

from services.text_language import detect_language


def test_arabic_text_is_ar():
    assert detect_language("الخدمة ممتازة وسريعة") == "ar"


def test_english_text_is_en():
    assert detect_language("The service was fast and clear.") == "en"


def test_half_arabic_half_latin_letters_is_ar():
    # Four Arabic letters and four Latin letters: at least half are Arabic.
    assert detect_language("جيدة good") == "ar"


def test_latin_with_accents_is_en():
    assert detect_language("Très bien, café") == "en"


def test_other_script_is_other():
    assert detect_language("Очень хорошо") == "other"


@pytest.mark.parametrize("text", ["123 !!!", "١٢٣ ؟ 456", "...", "   "])
def test_digits_and_punctuation_only_have_no_language(text):
    assert detect_language(text) is None


@pytest.mark.parametrize("text", ["", None])
def test_empty_text_has_no_language(text):
    assert detect_language(text) is None
