

from django import newforms as forms
from django.contrib.auth.models import User

__all__ = ['PasswordResetForm','NewPasswordSetForm']

class PasswordResetForm(forms.Form):

    username  = forms.CharField(max_length=64,
                                help_text = '(Case sensitive)')
    last_name = forms.CharField(max_length=64, label="Last Name")

    def clean_username(self):

        try:
            user = User.objects.get(username=self.clean_data['username'])
        except User.DoesNotExist:
            raise forms.ValidationError, "User '%s' does not exist." % self.clean_data['username']

        return self.clean_data['username'].strip()

    def clean_last_name(self):

        try:
            user = User.objects.get(username=self.clean_data['username'],
                                    last_name__iexact=self.clean_data['last_name'].strip())
        except User.DoesNotExist:
            raise forms.ValidationError, "Last name, '%s', does not match user." % self.clean_data['last_name']
        
        return self.clean_data['last_name'].strip()

class NewPasswordSetForm(forms.Form):

    code     = forms.CharField(widget = forms.HiddenInput())
    username = forms.CharField(max_length=128,
                               help_text='(The one you used to receive the email.)')
    password = forms.CharField(max_length=128, min_length=5,widget=forms.PasswordInput())
    password_confirm = forms.CharField(max_length = 128,widget=forms.PasswordInput(),
                                       label='Password Confirmation')

    def clean_username(self):
        try:
            user = User.objects.get(username = self.clean_data['username'].strip(),
                                    password = self.clean_data['code'])
        except User.DoesNotExist:
            raise forms.ValidationError('Invalid username.')

        return self.clean_data['username'].strip()
    

    def clean_password_confirm(self):
        new_passwd= self.clean_data['password_confirm'].strip()

        if self.clean_data['password'] != new_passwd:
            raise forms.ValidationError('Password and confirmation are not equal.')
        return new_passwd
