import django.forms as forms
from django.contrib.localflavor.usa.us_states import STATE_CHOICES



class ContactInfoForm(forms.Form):
    first_name = forms.CharField()
    last_name  = forms.CharField()
    e_mail     = forms.EmailField()
    address_street = forms.CharField(label="Street Address")
    address_city   = forms.CharField()
#    address_
