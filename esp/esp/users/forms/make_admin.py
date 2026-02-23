from django import forms
from esp.db.forms import AjaxForeignKeyNewformField
from esp.users.models import ESPUser

class MakeAdminForm(forms.Form):
    target_user = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='target_user', label='Target User',
        help_text='This account will be granted administrator privileges.')
