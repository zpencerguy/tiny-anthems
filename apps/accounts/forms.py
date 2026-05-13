from django import forms


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="Email")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
