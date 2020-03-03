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
        super(QuestionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Question
        exclude = ['param_values']

# class ClassroomImportForm(forms.Form):
    # program = forms.ModelChoiceField(queryset=None)
    # complete_availability = forms.BooleanField(required=False, help_text='Check this box if you would like the new classrooms to be available at all times during the program, rather than attempting to replicate their availability from the previous program.')
    # import_furnishings = forms.BooleanField(required=False, help_text='Check this box if you would like the new classrooms to have the same furnishings as they did for the previous program.')

    # def __init__(self, *args, **kwargs):
        # cur_prog = kwargs.pop('cur_prog', None)
        # super(ClassroomImportForm, self).__init__(*args, **kwargs)
        # progs = Resource.objects.filter(res_type=ResourceType.get_or_create('Classroom')).values_list('event__program', flat = True).distinct()
        # qs = Program.objects.filter(id__in=progs)
        # if cur_prog is not None:
            # qs = qs.exclude(id=cur_prog.id)
        # self.fields['program'].queryset = qs
