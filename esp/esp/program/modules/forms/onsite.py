from django import forms
from esp.program.models import RegistrationProfile
from esp.db.forms import AjaxForeignKeyNewformField

class OnSiteRegForm(forms.Form):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':20, 'class':'required'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':30, 'class':'required'}))
    email = forms.EmailField(max_length=75, widget=forms.TextInput({'size':20, 'class':'required'}))

    grade = forms.ChoiceField(choices = zip(range(7, 13), range(7, 13)), widget=forms.Select({'class':'required'}))

    paid = forms.BooleanField(required = False)
    medical = forms.BooleanField(required = False)
    liability = forms.BooleanField(required = False)
        
class OnSiteSATPrepRegForm(forms.Form):
    # TODO: Would like to subclass OnSiteRegForm, but this one lacks the grade entry
    first_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':20, 'class':'required'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput({'size':30, 'class':'required'}))
    email = forms.EmailField(max_length=75, widget=forms.TextInput({'size':20, 'class':'required'}))

    paid = forms.BooleanField(required = False)
    medical = forms.BooleanField(required = False)
    liability = forms.BooleanField(required = False)

    from esp.program.modules.forms.satprep import SATScoreField
    old_math_score = SATScoreField(required = False)
    old_verb_score = SATScoreField(required = False)
    old_writ_score = SATScoreField(required = False)


class OnSiteRapidCheckinForm(forms.Form):
    user = AjaxForeignKeyNewformField(field=RegistrationProfile.user.field, label='Student')
