from django import forms

choice_tuples = (('diag', 'Diagnostic Exam'), ('prac', 'Practice Exam'))

class ScoreUploadForm(forms.Form):
    test = forms.ChoiceField(label='Type of SAT test', choices=choice_tuples)
    file = forms.Field(required=False, widget=forms.FileInput, label='Upload score file', help_text='Please use the specified comma-separated variable (CSV) format.')
    text = forms.CharField(required=False, label='Enter CSV scores directly', help_text='If you enter scores here, the file will be ignored.', widget=forms.Textarea(attrs={'rows': 10, 'cols': 50}))
    

