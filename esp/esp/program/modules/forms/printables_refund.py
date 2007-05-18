import django.newforms as forms



class RefundInfoForm(forms.Form):
    payer_name = forms.CharField(help_text = 'The name from the credit card purchase.')
    payer_address = forms.CharField()
    userid = forms.CharField(widget=forms.HiddenInput)
