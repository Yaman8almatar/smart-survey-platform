from django import forms

from core.enums import Gender


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css_class


class DemographicProfileForm(BootstrapFormMixin, forms.Form):
    age = forms.IntegerField()
    gender = forms.ChoiceField(
        choices=[
            (Gender.MALE, Gender.MALE.label),
            (Gender.FEMALE, Gender.FEMALE.label),
        ]
    )
    region = forms.CharField(max_length=255)
    interests = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
