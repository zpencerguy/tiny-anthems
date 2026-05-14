from django import forms

from .models import SongRequest
from .sanitization import normalize_single_line, normalize_text


class NormalizedEmailField(forms.EmailField):
    def to_python(self, value):
        return super().to_python(normalize_single_line(value).lower())


class NormalizedCharField(forms.CharField):
    def to_python(self, value):
        return super().to_python(normalize_single_line(value))


class NormalizedTextField(forms.CharField):
    def to_python(self, value):
        return super().to_python(normalize_text(value))


class SongRequestForm(forms.ModelForm):
    email = NormalizedEmailField()
    generated_title = NormalizedCharField(
        required=False,
        label="Song title",
        help_text="Optional. This is used on the song page and as the download filename.",
    )
    recipient_name = NormalizedCharField()
    recipient_nickname = NormalizedCharField(required=False)
    milestone = NormalizedCharField(required=False)
    personal_details = NormalizedTextField(widget=forms.Textarea(attrs={"rows": 5}))
    things_to_avoid = NormalizedTextField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = SongRequest
        fields = [
            "email",
            "generated_title",
            "occasion",
            "recipient_name",
            "recipient_nickname",
            "milestone",
            "relationship",
            "personal_details",
            "things_to_avoid",
            "family_friendly",
            "vibe",
            "tone",
        ]

    def clean_email(self):
        return normalize_single_line(self.cleaned_data["email"]).lower()

    def clean_generated_title(self):
        title = normalize_single_line(self.cleaned_data["generated_title"])
        if len(title) > 120:
            raise forms.ValidationError("Keep the song title under 120 characters.")
        return title

    def clean_recipient_name(self):
        return normalize_single_line(self.cleaned_data["recipient_name"])

    def clean_recipient_nickname(self):
        return normalize_single_line(self.cleaned_data["recipient_nickname"])

    def clean_milestone(self):
        return normalize_single_line(self.cleaned_data["milestone"])

    def clean_personal_details(self):
        details = normalize_text(self.cleaned_data["personal_details"])
        if len(details) < 20:
            raise forms.ValidationError("Add at least 20 characters of personal details.")
        if len(details) > 1000:
            raise forms.ValidationError("Keep details under 1,000 characters.")
        blocked = ["taylor swift", "drake", "beyonce", "olivia rodrigo", "bad bunny"]
        if any(name in details.lower() for name in blocked):
            raise forms.ValidationError(
                "Please describe the musical feel without naming artists to imitate."
            )
        return details

    def clean_things_to_avoid(self):
        avoid = normalize_text(self.cleaned_data["things_to_avoid"])
        if len(avoid) > 500:
            raise forms.ValidationError("Keep things to avoid under 500 characters.")
        return avoid
