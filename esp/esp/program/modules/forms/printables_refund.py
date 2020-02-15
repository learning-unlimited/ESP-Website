import django.forms as forms



class RefundInfoForm(forms.Form):
    payer_name = forms.CharField(help_text = 'The name from the credit card purchase.')
    payer_address = forms.CharField()
    userid = forms.CharField(widget=forms.HiddenInput)
    credit_card_num = forms.CharField(max_length=255, required=False, help_text="The CreditCard number used.")
    omars_number = forms.CharField(max_length=64, required=False, help_text="The number on OMARs form.")
    txn_amount = forms.CharField(max_length=10, required=False, help_text="The amount of money to refund, in case we don't have transaction data. (Please use only if you are VERY sure.)")

