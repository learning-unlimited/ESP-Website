from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from esp.cal.models import Event
from esp.program.models import RegistrationType
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator

def get_rt_choices():
    choices = [("All","All")]
    for rt in RegistrationType.objects.all().order_by('name'):
        if rt.displayName:
            choices.append((rt.name, '%s (displayed as "%s")' % (rt.name, rt.displayName)))
        else:
            choices.append((rt.name, rt.name))
    return choices

class VisibleRegistrationTypeForm(forms.Form):
    display_names = forms.MultipleChoiceField(choices=get_rt_choices(), required=False, label='', help_text=mark_safe("<br />Select the Registration Types that should be displayed on a student's schedule on the studentreg page. To select an entry, hold Ctrl (on Windows or Linux) or Meta (on Mac), and then press it with your mouse."), widget=forms.SelectMultiple(attrs={'style':'height:150px; background:white;'}))


class LunchConstraintsForm(forms.Form):
    def __init__(self, program, *args, **kwargs):
        self.program = program

        super(LunchConstraintsForm, self).__init__(*args, **kwargs)

        #   Set choices for timeslot field
        self.fields['timeslots'].choices = [(ts.id, ts.short_description) for ts in self.program.getTimeSlots()]
        self.load_data()

    def load_data(self):
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').distinct()
        self.initial['timeslots'] = lunch_timeslots.values_list('id', flat=True)

    def save_data(self):
        timeslots = Event.objects.filter(id__in=self.cleaned_data['timeslots']).order_by('start')
        cg = LunchConstraintGenerator(self.program, timeslots, generate_constraints=(self.cleaned_data['generate_constraints'] is True), autocorrect=(self.cleaned_data['autocorrect'] is True), include_conditions=(self.cleaned_data['include_conditions'] is True))
        cg.generate_all_constraints()

    timeslots = forms.MultipleChoiceField(choices=[], required=False, widget=forms.CheckboxSelectMultiple)

    generate_constraints=forms.BooleanField(initial=True, required=False, help_text="Check this box to generate lunch scheduling constraints. If unchecked, only lunch sections will be generated, and the other two check boxes will have no effect.")
    autocorrect = forms.BooleanField(initial=True, required=False, help_text="Check this box to attempt automatically adding lunch to a student's schedule so that they are less likely to violate the schedule constraint.")
    include_conditions = forms.BooleanField(initial=True, required=False, help_text="Check this box to allow students to schedule classes through lunch if they do not have morning or afternoon classes.")

