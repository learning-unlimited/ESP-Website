from django import forms
from django.core import validators
from esp.users.models import ESPUser

class UserRegManipulator(forms.Manipulator):
    """Manipulator for User Reg"""
    def __init__(self):
        confirm_validators = [validators.AlwaysMatchesOtherField('password','The password and confirmation password do not match.'),validators.isNotEmpty]
        roles = [('Student','ESP Student (up through 12th grade)'),
                 ('Teacher','ESP Teacher (MIT or non-MIT affiliated)'),
                 ('Guardian','Guardian of ESP student or potential student'),
                 ('Educator','K-12 Educator')]

        self.fields = (
            forms.TextField(field_name="username", length=12, maxlength=12,validator_list=[self.isUniqueUserName,validators.isNotEmpty],is_required=True),
            forms.TextField(field_name="first_name", length=12, maxlength=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="last_name", length=12, maxlength=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.PasswordField(field_name="password", length=12, maxlength=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.PasswordField(field_name="password_confirm", length=12, maxlength=32,validator_list=confirm_validators,is_required=True),
            forms.RadioSelectField(field_name='role',choices=roles,is_required=True),
            forms.EmailField(field_name="email",length=15, is_required=True)
            )

    def isUniqueUserName(self, field_data, all_data):
        if ESPUser.isUserNameTaken(field_data):
            raise validators.ValidationError, 'Username "'+field_data+'" already in use. Please use another one.'
