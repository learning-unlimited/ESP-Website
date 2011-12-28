from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from esp.program.models import RegistrationType

class VisibleRegistrationTypeForm(forms.Form):
    display_names = forms.MultipleChoiceField(choices=[("All","All")]+[(rt.name, rt.name) for rt in RegistrationType.objects.all().order_by('name')], required=False, label='', help_text=mark_safe("<br />Select the Registration Types that should be displayed on a student's schedule on the studentreg page. To select an entry, hold Ctrl (on Windows or Linux) or Meta (on Mac), and then press it with your mouse."), widget=forms.SelectMultiple(attrs={'style':'height:150px; background:white;'}))
    

