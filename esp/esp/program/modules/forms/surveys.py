from django import forms

from esp.survey.models  import Question, Survey

class SurveyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True, program = None, *args, **kwargs):
        survey = super().save(commit=False, *args, **kwargs)
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
        super().__init__(*args, **kwargs)
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

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        param_values_raw = cleaned_data.get('_param_values', '') or ''
        if param_values_raw:
            params = [p.strip() for p in param_values_raw.split('|')]
        else:
            params = []

        if question_type:
            qt_name = question_type.name

            if qt_name in ('Multiple Choice', 'Checkboxes'):
                # params is the list of choices; require at least one non-empty choice
                choices = [p for p in params if p.strip()]
                if not choices:
                    raise forms.ValidationError(
                        'Please provide at least one choice for a %(qt)s question.',
                        params={'qt': qt_name},
                    )

            elif qt_name in ('Labeled Numeric Rating', 'Numeric Rating'):
                # First param is the number of ratings; must be an integer >= 2
                if not params or not params[0]:
                    raise forms.ValidationError(
                        '%(qt)s requires the number of ratings to be specified.',
                        params={'qt': qt_name},
                    )
                try:
                    num_ratings = int(params[0])
                except (ValueError, TypeError):
                    raise forms.ValidationError(
                        'Number of ratings must be a whole number, got "%(val)s".',
                        params={'val': params[0]},
                    )
                if num_ratings < 2:
                    raise forms.ValidationError(
                        'Number of ratings must be at least 2, got %(val)s.',
                        params={'val': num_ratings},
                    )

        return cleaned_data

class SurveyImportForm(forms.Form):
    survey_id = forms.ModelChoiceField(queryset=None, label = "Survey")

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super().__init__(*args, **kwargs)
        self.fields['survey_id'].queryset = Survey.objects.exclude(program=cur_prog)
