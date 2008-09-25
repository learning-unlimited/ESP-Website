from django import forms

choice_tuples = (('diag', 'Diagnostic Exam'), ('prac', 'Practice Exam'))

class ScoreUploadForm(forms.Form):
    test = forms.ChoiceField(label='Type of SAT test', choices=choice_tuples)
    file = forms.Field(required=False, widget=forms.FileInput, label='Upload score file', help_text='Please use the specified comma-separated variable (CSV) format.')
    text = forms.CharField(required=False, label='Enter CSV scores directly', help_text='If you enter scores here, the file will be ignored.', widget=forms.Textarea(attrs={'rows': 10, 'cols': 50}))
    

from esp.program.modules.module_ext import SATPrepTeacherModuleInfo
class SATPrepTeacherInfoForm(forms.ModelForm):
    sat_math = forms.IntegerField(min_value = 200, max_value = 800, required = False, widget = forms.TextInput({'size':3, 'maxlength':3}))
    sat_verb = forms.IntegerField(min_value = 200, max_value = 800, required = False, widget = forms.TextInput({'size':3, 'maxlength':3}))
    sat_writ = forms.IntegerField(min_value = 200, max_value = 800, required = False, widget = forms.TextInput({'size':3, 'maxlength':3}))
    mitid = forms.RegexField(regex = r'[0-9]{9}', max_length = 9, widget = forms.TextInput({'size':10, 'class':'required'}),
	    error_messages={'invalid':'Not a valid MIT id.'})

    def __init__(self, subjects=None, *args, **kwargs):
        self.base_fields['subject'] = forms.ChoiceField(choices = subjects, required = True, widget = forms.Select({'size':1, 'class':'required'}))
        super(SATPrepTeacherInfoForm, self).__init__(*args, **kwargs)

        error_messages = {'min_value':'The lowest SAT score is %s.', 'max_value':'The highest SAT score is %s.'}
        self.sat_math.error_messages = error_messages
        self.sat_verb.error_messages = error_messages
        self.sat_writ.error_messages = error_messages

    class Meta:
	model = SATPrepTeacherModuleInfo
	fields = ('sat_math', 'sat_verb', 'sat_writ', 'mitid', 'subject')

