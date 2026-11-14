from django import forms

from core.enums import Gender, Governorate, Interest


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                css_class = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            field.widget.attrs["class"] = css_class


class DemographicProfileForm(BootstrapFormMixin, forms.Form):
    age = forms.IntegerField()
    gender = forms.ChoiceField(
        choices=[
            (Gender.MALE, Gender.MALE.label),
            (Gender.FEMALE, Gender.FEMALE.label),
        ]
    )
    region = forms.ChoiceField(
        choices=[("", "Choose your governorate"), *Governorate.choices]
    )
    interests = forms.MultipleChoiceField(
        choices=Interest.choices,
        widget=forms.CheckboxSelectMultiple,
    )
