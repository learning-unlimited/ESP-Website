from django import forms
from esp.db.forms import AjaxForeignKeyNewformField
from esp.users.models import ESPUser

class UserMergeForm(forms.Form):
    absorber = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='absorber', label='Absorber',
        help_text='This account will become your main account.')
    absorbee = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='absorbee', label='Absorbee',
        help_text='Everything on this account will be moved to your main account.')
