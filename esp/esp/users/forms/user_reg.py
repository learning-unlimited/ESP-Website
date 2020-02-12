from django import forms
from django.db.models.query import Q
from django.forms.fields import HiddenInput, TextInput

from esp.users.models import ESPUser, GradeChangeRequest
from esp.utils.forms import StrippedCharField
from localflavor.us.forms import USPhoneNumberField

class ValidHostEmailField(forms.EmailField):
    """ An EmailField that runs a DNS query to make sure the host is valid. """

    def clean(self, value):
        """ Make sure the email address is sane """
        email = super(ValidHostEmailField, self).clean(value)
        email_parts = email.split("@")
        if len(email_parts) != 2:
            raise forms.ValidationError('Email addresses must be of the form "name@host"')

        email_host = email_parts[1].encode('ascii')

        try:
            import DNS
            try:
                DNS.DiscoverNameServers()
                if len(DNS.Request(qtype='a').req(email_host).answers) == 0 and len(DNS.Request(qtype='mx').req(email_host).answers) == 0:
                    raise forms.ValidationError('"%s" is not a valid email host' % email_host)
            except (IOError, DNS.DNSError): # (no resolv.conf, no nameservers)
                pass
        except ImportError: # no PyDNS
            pass

        return email

class EmailUserRegForm(forms.Form):
    email = ValidHostEmailField(help_text = "<i>Please provide an email address that you check regularly.</i>",max_length=75)
    confirm_email = ValidHostEmailField(label = "Confirm email", help_text = "<i>Please type your email address again.</i>",max_length=75)

    def clean_confirm_email(self):
        if not (('confirm_email' in self.cleaned_data) and ('email' in self.cleaned_data)) or (self.cleaned_data['confirm_email'] != self.cleaned_data['email']):
            raise forms.ValidationError('Ensure that you have correctly typed your email both times.')
        return self.cleaned_data['confirm_email']

class UserRegForm(forms.Form):
    """
    A form for users to register for the ESP web site.
    """
    first_name = StrippedCharField(max_length=30)
    last_name  = StrippedCharField(max_length=30)

    username = forms.CharField(min_length=5, max_length=30)

    password = forms.CharField(widget = forms.PasswordInput(),
                               min_length=5)

    confirm_password = forms.CharField(widget = forms.PasswordInput(),
                                       min_length=5)

    #   The choices for this field will be set later in __init__()
    initial_role = forms.ChoiceField(choices = [])

    email = ValidHostEmailField(help_text = "<i>Please provide an email address that you check regularly.</i>",max_length=75, widget=HiddenInput)
    confirm_email = ValidHostEmailField(label = "Confirm email", help_text = "<i>Please type your email address again.</i>",max_length=75, widget=HiddenInput)

    def clean_initial_role(self):
        data = self.cleaned_data['initial_role']
        if data == u'':
            raise forms.ValidationError('Please select an initial role')
        return data

    def clean_username(self):
        """ Make sure that 'username' (as provided as input to this form)
            only contains letters and numbers, and doesn't already exist """

        data = self.cleaned_data['username']

        import string
        good_chars = set(string.letters + string.digits)

        set_of_data = set(data)
        if not(good_chars & set_of_data == set_of_data):
            raise forms.ValidationError('Username contains invalid characters.')

        #   Check for duplicate accounts, but avoid triggering for users that are:
        #   - awaiting initial activation
        #   - currently on the email list only (they can be 'upgraded' to a full account)
        awaiting_activation = Q(is_active=False, password__regex='\$(.*)_')
        if ESPUser.objects.filter(username__iexact = data).exclude(password = 'emailuser').exclude(awaiting_activation).count() > 0:
            raise forms.ValidationError('Username already in use.')

        data = data.strip()
        return data

    def clean_confirm_password(self):
        if not (('confirm_password' in self.cleaned_data) and ('password' in self.cleaned_data)) or (self.cleaned_data['confirm_password'] != self.cleaned_data['password']):
            raise forms.ValidationError('Ensure the password and password confirmation are equal.')
        return self.cleaned_data['confirm_password']

    def clean_confirm_email(self):
        if not (('confirm_email' in self.cleaned_data) and ('email' in self.cleaned_data)) or (self.cleaned_data['confirm_email'] != self.cleaned_data['email']):
            raise forms.ValidationError('Ensure that you have correctly typed your email both times.')
        return self.cleaned_data['confirm_email']

    def __init__(self, *args, **kwargs):
        #   Set up the default form
        super(UserRegForm, self).__init__(*args, **kwargs)

        #   Adjust initial_role choices
        role_choices = [(item[0], item[1]['label']) for item in ESPUser.getAllUserTypes()]
        self.fields['initial_role'].choices = [('', 'Pick one...')] + role_choices

class SinglePhaseUserRegForm(UserRegForm):
    def __init__(self, *args, **kwargs):
        #email field not hidden
        super(SinglePhaseUserRegForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget = TextInput(attrs=self.fields['email'].widget.attrs)
        self.fields['confirm_email'].widget = TextInput(attrs=self.fields['confirm_email'].widget.attrs)

class AwaitingActivationEmailForm(forms.Form):
    """Form used to verify a user is yet to be activated"""
    username = forms.CharField(min_length=5, max_length=30)

    def clean_username(self):
        data = self.cleaned_data['username']
        awaiting_activation = Q(is_active=False, password__regex='\$(.*)_')
        if ESPUser.objects.filter(username__iexact = data).exclude(password = 'emailuser').filter(awaiting_activation).count() == 0:
            raise forms.ValidationError('That username isn\'t waiting to be activated.')

        data = data.strip()
        return data


class GradeChangeRequestForm(forms.ModelForm):
    """
    Form used by student to issue a grade change request.
    """
    class Meta:
        model = GradeChangeRequest
        exclude = ('acknowledged_by','acknowledged_time','requesting_student',
                   'approved', 'grade_before_request',)
