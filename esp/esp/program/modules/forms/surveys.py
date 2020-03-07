from django import forms

from esp.survey.models  import QuestionType, Question, Survey

class SurveyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SurveyForm, self).__init__(*args, **kwargs)

    def save(self, commit=True, program = None, *args, **kwargs):
        survey = super(SurveyForm, self).save(commit=False, *args, **kwargs)
        survey.program = program
        if commit:
            survey.save()
        return survey

    class Meta:
        model = Survey
        exclude = ['program']

class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        surveys = Survey.objects.filter(program=cur_prog)
        self.base_fields['survey'].choices = ((str(survey.id), survey.name + " (" + survey.category + ")") for survey in surveys)
        super(QuestionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Question
        exclude = ['param_values']

class SurveyImportForm(forms.Form):
    survey = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(SurveyImportForm, self).__init__(*args, **kwargs)
        self.fields['survey'].queryset = Survey.objects.exclude(program=cur_prog)
