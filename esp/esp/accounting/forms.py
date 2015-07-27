# coding: utf-8
from django import forms
from models import Program
from esp.accounting.models import LineItemType

FILE_TYPES = (
    ('html', 'HTML'),
    ('csv', 'CVS'),
    ('pdf', 'PDF'),
)


class TransferDetailsReportForm(forms.Form):
    program = forms.ChoiceField(required=False)
    from_date = forms.DateField(required=False, label='Dates')
    to_date = forms.DateField(required=False, label='To')
    file_type = forms.ChoiceField(widget=forms.HiddenInput, required=False, choices=FILE_TYPES)

    def __init__(self, *args, **kwargs):
        if 'user_programs' in kwargs:
            self.user_programs = kwargs.pop('user_programs')

        super(TransferDetailsReportForm, self).__init__(*args, **kwargs)

        program_options = [('', 'All')] + [(program.id, program.name) for program in self.user_programs]
        self.fields['program'].choices = program_options

        for s in ('from_date','to_date',):
            self.fields[s].widget.attrs['class'] = 'input-small'

