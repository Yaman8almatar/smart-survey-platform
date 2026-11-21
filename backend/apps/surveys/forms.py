from django import forms

from core.enums import (
    QUESTION_TYPE_LABELS,
    Education,
    Gender,
    Governorate,
    Interest,
    MaritalStatus,
    Occupation,
    QuestionType,
)
from services.targeting_service import TargetingService


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Chips and segments are styled by their label (site.css), never as form-control.
            if isinstance(field.widget, forms.RadioSelect):
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            field.widget.attrs["class"] = css_class


class SurveyForm(BootstrapFormMixin, forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    # FR-16: the respondent's own order of questions and of multiple-choice options.
    shuffle_questions = forms.BooleanField(required=False)
    shuffle_options = forms.BooleanField(required=False)
    # FR-11: the limit has no min or max here, so the service's messages are the ones shown.
    opens_on = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    closes_on = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    target_responses = forms.IntegerField(required=False)


class QuestionForm(BootstrapFormMixin, forms.Form):
    question_text = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    question_type = forms.ChoiceField(
        choices=[(value, QUESTION_TYPE_LABELS[value]) for value in QuestionType.values],
    )
    is_required = forms.BooleanField(required=False, initial=True)
    order_index = forms.IntegerField()
    options = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="For multiple-choice questions, enter one option per line.",
    )
    # FR-04 (W-04): the attention option and its expected answer.
    is_attention_check = forms.BooleanField(required=False)
    # The 0-based position among the non-blank option lines; the template renders the radios.
    expected_option = forms.IntegerField(required=False, min_value=0)
    expected_rating = forms.TypedChoiceField(
        required=False,
        choices=[(value, str(value)) for value in range(1, 6)],
        coerce=int,
        empty_value=None,
        widget=forms.RadioSelect(attrs={"class": "visually-hidden"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound and self["is_attention_check"].value():
            # An attention check is always required; a disabled field keeps its initial True.
            self.fields["is_required"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("question_type") != QuestionType.MULTIPLE_CHOICE:
            # The option builder keeps lines typed under another type; only choices have options.
            cleaned_data["options"] = ""
        if not cleaned_data.get("is_attention_check"):
            # A hidden radio may still be posted; an ordinary question has no expected answer.
            cleaned_data["expected_option"] = None
            cleaned_data["expected_rating"] = None
            return cleaned_data

        # The disabled checkbox is not posted.
        cleaned_data["is_required"] = True
        question_type = cleaned_data.get("question_type")
        if question_type == QuestionType.OPEN_TEXT:
            self.add_error(
                "is_attention_check",
                "Attention checks work on multiple-choice and rating questions.",
            )
        elif question_type == QuestionType.MULTIPLE_CHOICE:
            cleaned_data["expected_rating"] = None
            self._require_expected("expected_option")
        elif question_type == QuestionType.RATING_SCALE:
            cleaned_data["expected_option"] = None
            self._require_expected("expected_rating")
        return cleaned_data

    def _require_expected(self, name):
        """Add "Choose the expected answer." when the field is empty and has no other error."""
        if self.cleaned_data.get(name) is None and name not in self.errors:
            self.add_error(name, "Choose the expected answer.")

    def option_lines(self):
        """Return the non-blank option lines, read as QuestionService._normalize_options reads them."""
        value = self["options"].value() or ""
        return [line.strip() for line in value.splitlines() if line.strip()]

    def expected_option_rows(self):
        """Return the radio rows of the expected option: index, text and whether it is chosen."""
        chosen = str(self["expected_option"].value())
        return [
            {"index": index, "text": text, "checked": str(index) == chosen}
            for index, text in enumerate(self.option_lines())
        ]


def _targeting_choices(enum):
    """Return enum choices a provider may target; PREFER_NOT_TO_SAY is a profile answer only."""
    return [(value, label) for value, label in enum.choices if value != "PREFER_NOT_TO_SAY"]


def _chips(enum):
    """Return a list field shown as chips: real checkboxes, visually hidden, inside labels."""
    return forms.MultipleChoiceField(
        required=False,
        choices=_targeting_choices(enum),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "visually-hidden"}),
    )


def _age_field():
    """Return an optional age bound checked on its own field; min <= max is the service's rule."""
    return forms.IntegerField(
        required=False,
        min_value=0,
        max_value=TargetingService.MAX_AGE,
        widget=forms.NumberInput(attrs={"placeholder": "Any"}),
    )


class TargetingListsForm(BootstrapFormMixin, forms.Form):
    """Parses the W-03 criteria (page and reach endpoint): gender, two ages and five lists.

    Gender renders three radios; "" is still accepted (no choice), as the endpoint may send it.
    """

    gender = forms.ChoiceField(
        required=False,
        choices=[
            (Gender.ANY, Gender.ANY.label),
            (Gender.MALE, Gender.MALE.label),
            (Gender.FEMALE, Gender.FEMALE.label),
        ],
        widget=forms.RadioSelect(attrs={"class": "visually-hidden"}),
    )
    age_min = _age_field()
    age_max = _age_field()
    regions = _chips(Governorate)
    education_levels = _chips(Education)
    occupations = _chips(Occupation)
    marital_statuses = _chips(MaritalStatus)
    interests = _chips(Interest)
