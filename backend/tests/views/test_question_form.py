"""Question form: sentence-case question type labels (TASK-24B, issue #61); leftover options (TASK-47)."""

import pytest

from apps.surveys.forms import QuestionForm


def bound_form(question_type, options):
    return QuestionForm(
        data={
            "question_text": "How do you feel?",
            "question_type": question_type,
            "order_index": "0",
            "options": options,
        }
    )


@pytest.mark.parametrize("question_type", ["RATING_SCALE", "OPEN_TEXT"])
def test_options_left_over_from_another_type_are_cleaned_away(question_type):
    form = bound_form(question_type, "Red\nBlue")

    assert form.is_valid(), form.errors
    assert form.cleaned_data["options"] == ""
    # The bound field keeps what was posted, for a redisplay.
    assert form.option_lines() == ["Red", "Blue"]


def test_a_multiple_choice_question_keeps_its_options():
    form = bound_form("MULTIPLE_CHOICE", "Red\nBlue")

    assert form.is_valid(), form.errors
    assert form.cleaned_data["options"] == "Red\nBlue"


def test_question_form_offers_sentence_case_question_types_in_enum_order():
    choices = list(QuestionForm().fields["question_type"].choices)

    assert choices == [
        ("MULTIPLE_CHOICE", "Multiple choice"),
        ("RATING_SCALE", "Rating scale"),
        ("OPEN_TEXT", "Open text"),
    ]
