

from django import forms
from esp.users.models import ESPUser, PasswordRecoveryTicket
from django.utils.html import conditional_escape, mark_safe
from esp.utils.forms import FormWithRequiredCss, SizedCharField

__all__ = ['PasswordResetForm','NewPasswordSetForm', 'UserPasswdForm']

class PasswordResetForm(forms.Form):

    email     = forms.EmailField(max_length=75, required=False,
                                 help_text=mark_safe("(e.g. yourname@example.org)<br><br>---------- or ----------<br><br>"))

    username  = forms.CharField(max_length=30, required=False,
                                help_text = '(Case sensitive)')



    def clean_username(self):

        if self.cleaned_data.get('username','').strip() == '' and \
           self.cleaned_data.get('email','').strip() == '':
            raise forms.ValidationError("You need to specify something.")

        if self.cleaned_data['username'].strip() == '': return ''

        try:
            user = ESPUser.objects.get(username=self.cleaned_data['username'])
        except ESPUser.DoesNotExist:
            raise forms.ValidationError, "User '%s' does not exist." % self.cleaned_data['username']

        return self.cleaned_data['username'].strip()

    def clean_email(self):
        if self.cleaned_data['email'].strip() == '':
            return ''

        if len(ESPUser.objects.filter(email__iexact=self.cleaned_data['email']).values('id')[:1])>0:
            return self.cleaned_data['email'].strip()

        raise forms.ValidationError('No user has email %s' % self.cleaned_data['email'])


class NewPasswordSetForm(forms.Form):

    code     = forms.CharField(widget = forms.HiddenInput())
    username = forms.CharField(max_length=128,
                               help_text=mark_safe('(The one you used to receive the email.)<br/><br/>'))
    password = forms.CharField(max_length=128, min_length=5,widget=forms.PasswordInput())
    password_confirm = forms.CharField(max_length = 128,widget=forms.PasswordInput(),
                                       label='Password Confirmation')

    def clean_username(self):
        from esp.middleware import ESPError
        username = self.cleaned_data['username'].strip()
        if not 'code' in self.cleaned_data:
            raise ESPError("The form that you submitted does not contain a valid password-reset code.  If you arrived at this form from an email, are you certain that you used the entire URL from the email (including the bit after '?code=')?", log=False)
        try:
            ticket = PasswordRecoveryTicket.objects.get(recover_key = self.cleaned_data['code'], user__username = username)
        except PasswordRecoveryTicket.DoesNotExist:
            raise forms.ValidationError('Invalid username.')

        return username


    def clean_password_confirm(self):
        new_passwd = self.cleaned_data['password_confirm'].strip()

        if not 'password' in self.cleaned_data:
            raise forms.ValidationError('Invalid password; confirmation failed')

        if self.cleaned_data['password'] != new_passwd:
            raise forms.ValidationError('Password and confirmation are not equal.')
        return new_passwd

class UserPasswdForm(FormWithRequiredCss):
    password = SizedCharField(length=12, max_length=32, widget=forms.PasswordInput())
    newpasswd = SizedCharField(length=12, max_length=32, widget=forms.PasswordInput())
    newpasswdconfirm = SizedCharField(length=12, max_length=32, widget=forms.PasswordInput())

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserPasswdForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        if self.user is None:
            raise forms.ValidationError('Error: Not logged in.')
        current_passwd = self.cleaned_data['password']
        if not self.user.check_password(current_passwd):
            raise forms.ValidationError(mark_safe('As a security measure, please enter your <strong>current</strong> password.'))
        return current_passwd

    def clean_newpasswdconfirm(self):
        new_passwd = self.cleaned_data['newpasswdconfirm'].strip()

        if not 'newpasswd' in self.cleaned_data:
            raise forms.ValidationError('Invalid password; confirmation failed')

        if self.cleaned_data['newpasswd'] != new_passwd:
            raise forms.ValidationError('Password and confirmation are not equal.')
        return new_passwd
