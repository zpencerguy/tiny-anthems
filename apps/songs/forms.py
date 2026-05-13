from django import forms

from .models import SongRequest


class SongRequestForm(forms.ModelForm):
    class Meta:
        model = SongRequest
        fields = [
            "email",
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
        widgets = {
            "personal_details": forms.Textarea(attrs={"rows": 5}),
            "things_to_avoid": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_personal_details(self):
        details = self.cleaned_data["personal_details"].strip()
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
