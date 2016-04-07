

from django import forms


choices = zip(range(11),range(11))

class JunctionTeacherReview(forms.Form):
    score = forms.ChoiceField(choices = choices,
                              help_text = '10 being best, 0 being worst')

    rejected = forms.BooleanField(required = False,
                                  help_text = 'If you want to reject them outright.')

