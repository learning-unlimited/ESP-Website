
from django import forms
from django.contrib.auth.models import User

from esp.utils.forms import CaptchaForm, SizedCharField
from esp.users.forms.user_profile import PhoneNumberField

role_choices = (
    ('Student', 'Student (12th grade or lower)'),
    ('Teacher', 'Volunteer Teacher'),
    ('Guardian', 'Guardian of Student'),
    ('Educator', 'K-12 Educator'),
    )

class ValidHostEmailField(forms.EmailField):
    """ An EmailField that runs a DNS query to make sure the host is valid. """

    def clean(self, value):
        """ Make sure the e-mail address is sane """
        email = super(ValidHostEmailField, self).clean(value)
        email_parts = email.split("@")
        if len(email_parts) != 2:
            raise forms.ValidationError('E-mail addresses must be of the form "name@host"')

        email_host = email_parts[1].encode('ascii')

        try:
            import DNS
            try:
                DNS.DiscoverNameServers()
                if len(DNS.Request(qtype='a').req(email_host).answers) == 0 and len(DNS.Request(qtype='mx').req(email_host).answers) == 0:
                    raise forms.ValidationError('"%s" is not a valid e-mail host' % email_host)
            except (IOError, DNS.DNSError): # (no resolv.conf, no nameservers)
                pass
        except ImportError: # no PyDNS
            pass

        return email

class UserRegForm(forms.Form):
    """
    A form for users to register for the ESP web site.
    """
    email = ValidHostEmailField(help_text = "Please provide a valid email address.",max_length=75)

    first_name = forms.CharField(label = "First Name", max_length=30)
    last_name  = forms.CharField(label = "Last Name", max_length=30)

    username = forms.CharField(help_text="At least 5 characters, must contain only alphanumeric characters.",
                               min_length=5, max_length=30)


    password = forms.CharField(widget = forms.PasswordInput(),
                               min_length=5)

    confirm_password = forms.CharField(widget = forms.PasswordInput(),
                                       min_length=5)

    initial_role = forms.ChoiceField(label = "I am a...", choices = role_choices)

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

        if User.objects.filter(username__iexact = data).count() > 0:
            raise forms.ValidationError('Username already in use.')

        data = data.strip()
        return data

    def clean_confirm_password(self):
        if not (('confirm_password' in self.cleaned_data) and ('password' in self.cleaned_data)) or (self.cleaned_data['confirm_password'] != self.cleaned_data['password']):
            raise forms.ValidationError('Ensure the password and password confirmation are equal.')
        return self.cleaned_data['confirm_password']


#class EmailUserForm(CaptchaForm):
class EmailUserForm(forms.Form):
    email = ValidHostEmailField(help_text = '(e.g. johndoe@domain.xyz)')


class EmailPrefForm(forms.Form):
    email = ValidHostEmailField(label='E-Mail Address', required = True)
    first_name = SizedCharField(label='First Name', length=30, max_length=64, required=True)
    last_name = SizedCharField(label='Last Name', length=30, max_length=64, required=True)
    sms_number = PhoneNumberField(label='Cell Phone', required = False,
                                  help_text='Optional: If you provide us your cell phone number, we can send you SMS text notifications')
#    sms_opt_in = forms.BooleanField(label='Send Me Text Updates', initial = True, required = False)
