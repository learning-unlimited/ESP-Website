

from django import newforms as forms
from django.contrib.auth.models import User

__all__ = ['PasswordResetForm','NewPasswordSetForm']

class PasswordResetForm(forms.Form):

    email     = forms.EmailField(max_length=64, required=False,
                                 help_text="(e.g. johndoe@example.org)")

    username  = forms.CharField(max_length=64, required=False,
                                help_text = '(Case sensitive)')

    def clean_username(self):

        if self.clean_data.get('username','').strip() == '' and \
           self.clean_data.get('email','').strip() == '':
            raise forms.ValidationError("You need to specify something.")

        if self.clean_data['username'].strip() == '': return ''

        try:
            user = User.objects.get(username=self.clean_data['username'])
        except User.DoesNotExist:
            raise forms.ValidationError, "User '%s' does not exist." % self.clean_data['username']

        return self.clean_data['username'].strip()

    def clean_email(self):
        if self.clean_data['email'].strip() == '':
            return ''

        if len(User.objects.filter(email__iexact=self.clean_data['email']).values('id')[:1])>0:
            return self.clean_data['email'].strip()

        raise forms.ValidationError('No user has email %s' % self.clean_data['email'])


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
