from django import forms

choice_tuples = (('diag', 'Diagnostic Exam'), ('prac', 'Practice Exam'))

class ScoreUploadForm(forms.Form):
    test = forms.ChoiceField(label='Type of SAT test', choices=choice_tuples)
    file = forms.Field(required=False, widget=forms.FileInput, label='Upload score file', help_text='Please use the specified comma-separated variable (CSV) format.')
    text = forms.CharField(required=False, label='Enter CSV scores directly', help_text='If you enter scores here, the file will be ignored.', widget=forms.Textarea(attrs={'rows': 10, 'cols': 50}))

class SATScoreField(forms.IntegerField):
    def __init__(self, *args, **kwargs):
	forms.IntegerField.__init__(self,
		min_value = 200, max_value = 800,
		widget = forms.TextInput({'size':3, 'maxlength':3}),
		error_messages = {'min_value':'The lowest SAT score is %s.', 'max_value':'The highest SAT score is %s.'},
		*args, **kwargs)


class SATPrepTeacherInfoForm(forms.ModelForm):
    sat_math = SATScoreField(required = False)
    sat_verb = SATScoreField(required = False)
    sat_writ = SATScoreField(required = False)
    mitid = forms.RegexField(regex = r'[0-9]{9}', max_length = 9, widget = forms.TextInput({'size':10, 'class':'required'}),
	    error_messages={'invalid':'Not a valid MIT id.'})

    def __init__(self, subjects=None, *args, **kwargs):
        self.base_fields['subject'] = forms.ChoiceField(choices = subjects, required = True, widget = forms.Select({'size':1, 'class':'required'}))
        super(SATPrepTeacherInfoForm, self).__init__(*args, **kwargs)

    class Meta:
	from esp.program.modules.module_ext import SATPrepTeacherModuleInfo
	model = SATPrepTeacherModuleInfo
	fields = ('sat_math', 'sat_verb', 'sat_writ', 'mitid', 'subject')


class SATPrepDiagForm(forms.ModelForm):
    diag_math_score = SATScoreField(required = False)
    diag_verb_score = SATScoreField(required = False)
    diag_writ_score = SATScoreField(required = False)
    prac_math_score = SATScoreField(required = False)
    prac_verb_score = SATScoreField(required = False)
    prac_writ_score = SATScoreField(required = False)
    class Meta:
	from esp.program.models import SATPrepRegInfo
	model = SATPrepRegInfo
	fields = ('diag_math_score', 'diag_verb_score', 'diag_writ_score', 'prac_math_score', 'prac_verb_score', 'prac_writ_score')

class SATPrepInfoForm(forms.ModelForm):
    old_math_score = SATScoreField(required = False)
    old_verb_score = SATScoreField(required = False)
    old_writ_score = SATScoreField(required = False)

    heard_by = forms.CharField(max_length = 128, required = False, widget = forms.TextInput({'size':24}))
    class Meta:
	from esp.program.models import SATPrepRegInfo
	model = SATPrepRegInfo
	fields = ('old_math_score', 'old_verb_score', 'old_writ_score', 'heard_by')

class OnSiteRegForm(forms.Form):
    first_name = forms.CharField(max_length=64, widget=forms.TextInput({'size':20, 'class':'required'}))
    last_name = forms.CharField(max_length=64, widget=forms.TextInput({'size':30, 'class':'required'}))
    # TODO: A less stupid email regex?
    email = forms.RegexField(regex = r'[^ ]+@[^ ]+', max_length=64, widget = forms.TextInput({'size':20, 'class':'required'}),
	    error_messages={'invalid':'Not a valid email address.'})

    old_math_score = SATScoreField(required = False)
    old_verb_score = SATScoreField(required = False)
    old_writ_score = SATScoreField(required = False)

    paid = forms.BooleanField(required = False)
    medical = forms.BooleanField(required = False)
    liability = forms.BooleanField(required = False)
