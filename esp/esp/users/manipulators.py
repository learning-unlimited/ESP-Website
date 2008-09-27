
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django import oldforms as forms
from django.core import validators
from esp.users.models import ESPUser

class UserRegManipulator(forms.Manipulator):
    """Manipulator for User Reg"""
    def __init__(self):
        confirm_validators = [validators.AlwaysMatchesOtherField('password','The password and confirmation password do not match.'),validators.isNotEmpty]
        roles = [('Student','Student (up through 12th grade)'),
                 ('Teacher','Volunteer Teacher'),
                 ('Guardian','Guardian of Student'),
                 ('Educator','K-12 Educator')]

        self.fields = (
            forms.TextField(field_name="username", length=12, max_length=12,validator_list=[self.isUniqueUserName,validators.isNotEmpty],is_required=True),
            forms.TextField(field_name="first_name", length=12, max_length=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="last_name", length=12, max_length=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.PasswordField(field_name="password", length=12, max_length=32,is_required=True, validator_list=[validators.isNotEmpty]),
            forms.PasswordField(field_name="password_confirm", length=12, max_length=32,validator_list=confirm_validators,is_required=True),
            forms.RadioSelectField(field_name='role',choices=roles,is_required=True),
            forms.EmailField(field_name="email",length=15, is_required=True)
            )

    def isUniqueUserName(self, field_data, all_data):
        if ESPUser.isUserNameTaken(field_data):
            raise validators.ValidationError, 'Username "'+field_data+'" already in use. Please use another one.'

class UserRecoverForm(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="username", length=12, max_length=12, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="last_name",    length=50, max_length=60, is_required=True, validator_list=[IsValidEmailUserName])
            )

class SetPasswordForm(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="username", length=12, max_length=12, is_required=True, validator_list=[validators.isNotEmpty,IsValidCode]),
            forms.PasswordField(field_name="newpasswd", length=12, max_length=32, is_required = True),
            forms.TextField(field_name="code", is_required=True),
            forms.PasswordField(field_name="newpasswdconfirm", length=12, max_length=32, is_required = True,validator_list = [
                                validators.AlwaysMatchesOtherField('newpasswd', 'The new password and confirm password must be equal.')])
            )


def IsValidCode(field_data, all_data):
    from esp.users.models import User
    errormsg = 'Sorry, the username and code do not match.'
    try:
        user = User.objects.get(username = field_data)
    except:
        raise validators.ValidationError, errormsg

    if user.password.lower() != all_data['code'].lower():
        raise validators.ValidationError, errormsg    

def IsValidEmailUserName(field_data, all_data):
    from esp.users.models import User
    errormsg = 'Sorry, the username and last name do not match.'
    try:
        user = User.objects.get(username = all_data['username'])
    except:
        raise validators.ValidationError, errormsg

    if user.last_name.lower() != field_data.lower():
        raise validators.ValidationError, errormsg

class IsEqualTo(object):
    """ Form is equal to """
    def __init__(self, value):
        self.value = value

    def __call__(self, field_data, all_data):

        if field_data.strip() != self.value.strip():
            raise validators.ValidationError, 'Please enter the correct username.'
 
def UserPassCorrect(field_data, all_data):
    from django.contrib import auth
    user = auth.authenticate(username=all_data['username'].lower(), password=all_data['password'])
    if not user:
        raise validators.ValidationError, 'Username and/or password incorrect.'

