from django import forms
from esp.web.models import NavBarEntry

class NavBarEntryForm(forms.ModelForm):
    class Meta:
        model = NavBarEntry
        fields = '__all__'

    def clean_text(self):
        text = self.cleaned_data.get('text', '').strip()
        if not text:
            raise forms.ValidationError("NavBarEntry text cannot be empty.")
        return text