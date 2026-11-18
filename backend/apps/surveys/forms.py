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
