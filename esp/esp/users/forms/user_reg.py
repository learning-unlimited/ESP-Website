
from django import forms
from django.contrib.auth.models import User

role_choices = (
    ('Student', 'Student (up through 12th grade)'),
    ('Teacher', 'Volunteer Teacher'),
    ('Guardian', 'Guardian of Student'),
    ('Educator', 'K-12 Educator'),
    )

class UserRegForm(forms.Form):
    """
    A form for users to register for the ESP web site.
    """
    first_name = forms.CharField(max_length=30)
    last_name  = forms.CharField(max_length=30)

    username = forms.CharField(help_text="At least 5 characters, must contain only alphanumeric characters.",
                               min_length=5, max_length=30)


    password = forms.CharField(widget = forms.PasswordInput(),
                               min_length=5)

    confirm_password = forms.CharField(widget = forms.PasswordInput(),
                                       min_length=5)

    initial_role = forms.ChoiceField(choices = role_choices)

    email = forms.EmailField(help_text = "Please provide a valid email address. We won't spam you.",max_length=75)


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
        if self.cleaned_data['confirm_password'] != self.cleaned_data['password']:
            raise forms.ValidationError('Ensure the password and password confirmation are equal.')
        return self.cleaned_data['confirm_password']


    def clean_email(self):
        """ Make sure the e-mail address is sane """
        email = self.cleaned_data['email']
        email_parts = email.split("@")
        if len(email_parts) != 2:
            raise forms.ValidationError('E-mail addresses must be of the form "name@host"')

        email_host = email_parts[1]
        
        #import socket
        # aseering 9/10/2007 -- Oh, MX records; yeah...
        #socket.gethostbyname(email_host)

	# -- aseering 3/5/2008: This copy of the site has to work offline; we can't resolve DNS stuffs
        #import DNS
        #DNS.ParseResolvConf() # May or may not work on systems without a resolv.conf file
        #r = DNS.Request(qtype='mx')
        #res = r.req(email_host)
	#
        #if len(res.answers) == 0:
        #    raise forms.ValidationError('"%s" is not a valid e-mail host' % email_host)

        return email

class EmailUserForm(forms.Form):


    email = forms.EmailField(help_text = '(e.g. johndoe@domain.xyz)')

    def clean_email(self):
        """ Make sure the e-mail address is sane """
        email = self.cleaned_data['email']
        email_parts = email.split("@")
        if len(email_parts) != 2:
            raise forms.ValidationError('E-mail addresses must be of the form "name@host"')

        email_host = email_parts[1]
        
        import socket
        try:
            socket.gethostbyname(email_host)
        except socket.gaierror:
            raise forms.ValidationError('"%s" is not a valid e-mail host' % email_host)

        return email
