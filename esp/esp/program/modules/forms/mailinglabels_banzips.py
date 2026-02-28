import django.forms as forms


class BanZipsForm(forms.Form):
    zips = forms.CharField(label="List of zip codes", widget=forms.Textarea(attrs={'cols':'20', 'rows':'40'}),
                           help_text="One on each line, zip+4 (e.g. 02139-4030 on one line)")
