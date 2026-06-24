from django import forms
from esp.db.forms import AjaxForeignKeyNewformField
from esp.users.models import ESPUser

class UserMergeForm(forms.Form):
    absorber = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='absorber', label='Absorber',
        help_text='This account will become the main account.')
    absorbee = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='absorbee', label='Absorbee',
        help_text='Everything on this account will be moved to the main account.')
    forward = forms.BooleanField(label='Forward Login', required=False, initial=True,
        help_text='Should login forwarding be set up from the absorbee to the absorber?')
    deactivate = forms.BooleanField(label='Deactivate', required=False,
        help_text='Should the absorbee be deactivated?')

    def clean(self):
        cleaned_data = super().clean()
        absorber = cleaned_data.get("absorber")
        absorbee = cleaned_data.get("absorbee")
        if absorber and absorbee and absorber == absorbee:
            self.add_error('absorbee', "Absorber and Absorbee accounts cannot be the same.")
            if 'absorbee' in self.data:
                self.data = self.data.copy()
                self.data['absorber'] = ''
                self.data['absorbee'] = ''
        return cleaned_data
