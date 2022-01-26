from django import forms

from esp.survey.models  import Question, Survey

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
        help_texts = {
            'category': ('e.g. teach or learn'),
        }

class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        surveys = Survey.objects.filter(program=cur_prog)
        self.base_fields['survey'].choices = ((str(survey.id), survey.name + " (" + survey.category + ")") for survey in surveys)
        super(QuestionForm, self).__init__(*args, **kwargs)
        instance = kwargs.pop('instance', None)
        if instance:
            self.base_fields['survey'].initial = str(instance.id)

    class Meta:
        model = Question
        exclude = ['param_values']
        help_texts = {
            'name': ('This is the question that will be displayed to the user'),
            'per_class': ('Should this question be shown once for each class?'),
            'seq': ('Determines the order of the questions'),
            '_param_values': (),
        }
        labels = {
            'name': ('Question'),
            'question_type': ('Question Type'),
            'per_class': ('Per Class'),
            '_param_values': ('Parameter Values'),
            'seq': ('Sequence'),
        }

class SurveyImportForm(forms.Form):
    survey_id = forms.ModelChoiceField(queryset=None, label = "Survey")

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(SurveyImportForm, self).__init__(*args, **kwargs)
        self.fields['survey_id'].queryset = Survey.objects.exclude(program=cur_prog)
