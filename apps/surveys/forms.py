from django import forms

from core.enums import Gender, QuestionType


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
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
    question_type = forms.ChoiceField(choices=QuestionType.choices)
    is_required = forms.BooleanField(required=False, initial=True)
    order_index = forms.IntegerField()
    options = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="For multiple-choice questions, enter one option per line.",
    )


class TargetingCriteriaForm(BootstrapFormMixin, forms.Form):
    gender = forms.ChoiceField(
        required=False,
        choices=[
            ("", "No gender restriction"),
            (Gender.ANY, "Any gender"),
            (Gender.MALE, Gender.MALE.label),
            (Gender.FEMALE, Gender.FEMALE.label),
        ],
    )
    age_min = forms.IntegerField(required=False)
    age_max = forms.IntegerField(required=False)
    region = forms.CharField(required=False, max_length=255)
