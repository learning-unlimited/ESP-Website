# coding: utf-8
from datetime import datetime, timedelta
from django import forms
from models import Program
from esp.accounting.models import LineItemType
from django.forms import extras

#report from date should default to 30 days ago
FROM_DATE_DAYS_SINCE = 30

month_ago = lambda:datetime.now() - timedelta(days=FROM_DATE_DAYS_SINCE)

class TransferDetailsReportForm(forms.Form):
    program = forms.ChoiceField(required=False)
    from_date = forms.DateField(required=False, \
                                label='Dates', \
                                initial=month_ago)
    to_date = forms.DateField(required=False, label='To')

    def __init__(self, *args, **kwargs):
        if 'user_programs' in kwargs:
            self.user_programs = kwargs.pop('user_programs')
        print args
        super(TransferDetailsReportForm, self).__init__(*args, **kwargs)

        program_options = [('', 'All')] + [(program.id, program.name) \
                           for program in self.user_programs]

        self.fields['program'].choices = program_options

        for s in ('from_date','to_date',):
            self.fields[s].widget.attrs['class'] = 'input-small'
       
