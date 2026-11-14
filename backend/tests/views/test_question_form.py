"""Question form: sentence-case question type labels (TASK-24B, issue #61)."""

from apps.surveys.forms import QuestionForm


def test_question_form_offers_sentence_case_question_types_in_enum_order():
    choices = list(QuestionForm().fields["question_type"].choices)

    assert choices == [
        ("MULTIPLE_CHOICE", "Multiple choice"),
        ("RATING_SCALE", "Rating scale"),
        ("OPEN_TEXT", "Open text"),
    ]
