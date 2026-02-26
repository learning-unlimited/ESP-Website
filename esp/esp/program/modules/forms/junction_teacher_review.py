

from __future__ import absolute_import
from django import forms
from six.moves import range
from six.moves import zip


choices = list(zip(list(range(11)), list(range(11))))

class JunctionTeacherReview(forms.Form):
    score = forms.ChoiceField(choices = choices,
                              help_text = '10 being best, 0 being worst')

    rejected = forms.BooleanField(required = False,
                                  help_text = 'If you want to reject them outright.')

