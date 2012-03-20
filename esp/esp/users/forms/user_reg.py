
from django import forms
from django.contrib.auth.models import User
from django.db.models.query import Q

from esp.utils.forms import CaptchaForm
from esp.users.models import ESPUser

from esp.utils.forms import CaptchaForm, SizedCharField
from esp.users.forms.user_profile import PhoneNumberField

class ValidHostEmailField(forms.EmailField):
    """ An EmailField that runs a DNS query to make sure the host is valid. """

    def clean(self, value):
        """ Make sure the e-mail address is sane """
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
                    raise forms.ValidationError('This doesn\'t seem to be a real email address')
            except (IOError, DNS.DNSError): # (no resolv.conf, no nameservers)
                pass
        except ImportError: # no PyDNS
            pass

        return email

class UserRegForm(forms.Form):
    """
    A form for users to register for the ESP web site.
    """
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'onkeyup':'checkBasicText(this);','onblur':'checkErrorBasicText(this);'}))
    last_name  = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'onkeyup':'checkBasicText(this);','onblur':'checkErrorBasicText(this);'}))

    username = forms.CharField(help_text="At least 5 characters, must contain only alphanumeric characters.",
                               min_length=5, max_length=30, widget=forms.TextInput(attrs={'onkeyup':'checkUsername(this);', 'onblur':'checkErrorUsername(this);'}))


    password = forms.CharField(widget = forms.PasswordInput(attrs={'onkeyup':'checkPassword(this);','onblur':'checkErrorPassword(this);'}),
                               min_length=5)

    confirm_password = forms.CharField(widget = forms.PasswordInput(attrs={'onkeyup':'checkVerifyPassword(this);','onblur':'checkErrorVerifyPassword(this);'}),
                                       min_length=5)

    #   The choices for this field will be set later in __init__()
    initial_role = forms.ChoiceField(choices = [], widget=forms.Select(attrs={'onChange':'checkSelect(this);','onblur':'checkErrorSelect(this);'}))

    email = ValidHostEmailField(help_text = "Please provide a valid email address. We won't spam you.",max_length=75, widget=forms.TextInput(attrs={'onkeyup':'checkEmail(this);','onblur':'checkErrorEmail(this);'}))

    def clean_initial_role(self):
        data = self.cleaned_data['initial_role']
        if data == u'':
            raise forms.ValidationError('Don\'t forget to enter your role')
        return data

    def clean_username(self):
        """ Make sure that 'username' (as provided as input to this form)
            only contains letters and numbers, and doesn't already exist """

        data = self.cleaned_data['username']

        import string
        good_chars = set(string.letters + string.digits)

        set_of_data = set(data)
        if not(good_chars & set_of_data == set_of_data):
            raise forms.ValidationError('Only letters and numbers are allowed in a username (no spaces)')
 
        #   Check for duplicate accounts, but avoid triggering for users that are:
        #   - awaiting initial activation
        #   - currently on the e-mail list only (they can be 'upgraded' to a full account)
        awaiting_activation = Q(is_active=False, password__regex='\$(.*)_')
        if User.objects.filter(username__iexact = data).exclude(password = 'emailuser').exclude(awaiting_activation).count() > 0:
            raise forms.ValidationError('Unfortunately, this username is already in use.')

        data = data.strip()
        return data

    def clean_confirm_password(self):
        if not (('confirm_password' in self.cleaned_data) and ('password' in self.cleaned_data)) or (self.cleaned_data['confirm_password'] != self.cleaned_data['password']):
            raise forms.ValidationError('Make sure the password and password verification are the same.')
        return self.cleaned_data['confirm_password']

    def __init__(self, *args, **kwargs):
        #   Set up the default form
        super(UserRegForm, self).__init__(*args, **kwargs)
        
        #   Adjust initial_role choices
        user_types = ESPUser.getAllUserTypes()
        role_choices = [(item[0], item[1]['label']) for item in user_types]
        self.fields['initial_role'].choices = [('', 'Pick one...')] + role_choices
        

class EmailUserForm(CaptchaForm):
    email = ValidHostEmailField(help_text = '(e.g. johndoe@domain.xyz)')

class EmailPrefForm(forms.Form):
    email = ValidHostEmailField(label='E-Mail Address', required = True)
    first_name = SizedCharField(label='First Name', length=30, max_length=64, required=True)
    last_name = SizedCharField(label='Last Name', length=30, max_length=64, required=True)
    sms_number = PhoneNumberField(label='Cell Phone', required = False,
                                  help_text='Optional: If you provide us your cell phone number, we can send you SMS text notifications')
#    sms_opt_in = forms.BooleanField(label='Send Me Text Updates', initial = True, required = False)
