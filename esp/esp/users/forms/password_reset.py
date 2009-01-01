

from django import forms
from django.contrib.auth.models import User
from esp.users.models import PasswordRecoveryTicket
from django.utils.html import conditional_escape

__all__ = ['PasswordResetForm','NewPasswordSetForm', 'UserPasswdForm']

class PasswordResetForm(forms.Form):

    email     = forms.EmailField(max_length=75, required=False,
                                 help_text="(e.g. johndoe@example.org)")

    username  = forms.CharField(max_length=30, required=False,
                                help_text = '(Case sensitive)')


    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []
        first = True
        for name, field in self.fields.items():
            if not first:
                output.append(error_row % '<span class="or">- or -</span>')
            else:
                first = False
            bf = forms.forms.BoundField(self, field, name)
            bf_errors = forms.util.ErrorList([conditional_escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend(['(Hidden field %s) %s' % (name, e) for e in bf_errors])
                hidden_fields.append(unicode(bf))
            else:
                if errors_on_separate_row and bf_errors:
                    output.append(error_row % bf_errors)
                if bf.label:
                    label = conditional_escape(bf.label)
                    # Only add a colon if the label does not end in punctuation.
                    if label[-1] not in ':?.!':
                        label += ':'
                    label = bf.label_tag(label) or ''
                else:
                    label = ''
                if field.help_text:
                    help_text = help_text_html % field.help_text
                else:
                    help_text = u''
                output.append(normal_row % {'errors': bf_errors, 'label': label, 'field': unicode(bf), 'help_text': help_text})
        if top_errors:
            output.insert(0, error_row % top_errors)
        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = u''.join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and insert the hidden fields.
                output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
            else: # If there aren't any rows in the output, just append the hidden fields.
                output.append(str_hidden)
        return u'\n'.join(output)


    def clean_username(self):

        if self.cleaned_data.get('username','').strip() == '' and \
           self.cleaned_data.get('email','').strip() == '':
            raise forms.ValidationError("You need to specify something.")

        if self.cleaned_data['username'].strip() == '': return ''

        try:
            user = User.objects.get(username=self.cleaned_data['username'])
        except User.DoesNotExist:
            raise forms.ValidationError, "User '%s' does not exist." % self.cleaned_data['username']

        return self.cleaned_data['username'].strip()

    def clean_email(self):
        if self.cleaned_data['email'].strip() == '':
            return ''

        if len(User.objects.filter(email__iexact=self.cleaned_data['email']).values('id')[:1])>0:
            return self.cleaned_data['email'].strip()

        raise forms.ValidationError('No user has email %s' % self.cleaned_data['email'])


class NewPasswordSetForm(forms.Form):

    code     = forms.CharField(widget = forms.HiddenInput())
    username = forms.CharField(max_length=128,
                               help_text='(The one you used to receive the email.)')
    password = forms.CharField(max_length=128, min_length=5,widget=forms.PasswordInput())
    password_confirm = forms.CharField(max_length = 128,widget=forms.PasswordInput(),
                                       label='Password Confirmation')

    def clean_username(self):
        from esp.middleware import ESPError
        username = self.cleaned_data['username'].strip()
        if not self.cleaned_data.has_key('code'):
            raise ESPError(False), "The form that you submitted does not contain a valid password-reset code.  If you arrived at this form from an e-mail, are you certain that you used the entire URL from the e-mail (including the bit after '?code=')?"
        try:
            ticket = PasswordRecoveryTicket.objects.get(recover_key = self.cleaned_data['code'], user__username = username)
        except PasswordRecoveryTicket.DoesNotExist:
            raise forms.ValidationError('Invalid username.')

        return username
    

    def clean_password_confirm(self):
        new_passwd = self.cleaned_data['password_confirm'].strip()

        if not self.cleaned_data.has_key('password'):
            raise forms.ValidationError('Invalid password; confirmation failed')

        if self.cleaned_data['password'] != new_passwd:
            raise forms.ValidationError('Password and confirmation are not equal.')
        return new_passwd

class UserPasswdForm(forms.Form):
    password = forms.CharField(max_length=32, widget=forms.PasswordInput())
    newpasswd = forms.CharField(max_length=32, widget=forms.PasswordInput())
    newpasswdconfirm = forms.CharField(max_length=32, widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        for k,v in self.base_fields.items():
            if v.required:
                v.widget.attrs['class'] = 'required'
            v.widget.attrs['size'] = 12
        forms.Form.__init__(self, *args, **kwargs)

    def clean_newpasswdconfirm(self):
        new_passwd = self.cleaned_data['newpasswdconfirm'].strip()

        if not self.cleaned_data.has_key('newpasswd'):
            raise forms.ValidationError('Invalid password; confirmation failed')

        if self.cleaned_data['newpasswd'] != new_passwd:
            raise forms.ValidationError('Password and confirmation are not equal.')
        return new_passwd
