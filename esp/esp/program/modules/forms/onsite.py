from django import forms
from esp.db.forms import AjaxForeignKeyNewformField
from esp.utils.widgets import DateTimeWidget
from esp.users.models import K12School, ESPUser
import datetime

class OnSiteRegForm(forms.Form):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':20, 'class':'required'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':30, 'class':'required'}))
    email = forms.EmailField(max_length=75, widget=forms.TextInput({'size':20, 'class':'required'}))
    school = forms.CharField(max_length=128, widget=forms.HiddenInput, required=False)
    k12school = AjaxForeignKeyNewformField(key_type=K12School, field_name='k12school', shadow_field_name='school', required=False, label='School', help_text="(Type the school's name and click on a match if it pops up.)")

    grade = forms.ChoiceField(choices = zip(range(7, 13), range(7, 13)), widget=forms.Select({'class':'required'}))

    paid = forms.BooleanField(required = False)
    medical = forms.BooleanField(required = False)
    liability = forms.BooleanField(required = False)

    def __init__(self, *args, **kwargs):
        super(OnSiteRegForm, self).__init__(*args, **kwargs)
        self.fields['grade'].choices = (
            [('', '')] + [(x, x) for x in ESPUser.grade_options()])

class OnsiteBarcodeCheckinForm(forms.Form):
    uids = forms.CharField(label='',widget=forms.Textarea(attrs={'rows': 10}))

class TeacherCheckinForm(forms.Form):
    when = forms.DateTimeField(label='Date/Time', widget=DateTimeWidget, required = False)

    def __init__(self, *args, **kwargs):
        now = datetime.datetime.now()
        self.base_fields['when'].initial=datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(days=1, minutes=-1)
        super(TeacherCheckinForm, self).__init__(*args, **kwargs)
