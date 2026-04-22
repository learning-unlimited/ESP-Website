def clean(self):
    cleaned_data = super().clean()
    start = cleaned_data.get("start_date")
    end = cleaned_data.get("end_date")

    if start and end and end < start:
        raise forms.ValidationError("End date cannot be before start date")

    return cleaned_data
