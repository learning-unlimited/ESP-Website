from django import forms
from django.utils.safestring import mark_safe

from datetime import timedelta

from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.cal.models import EventType, Event
from esp.program.models import Program
from esp.utils.widgets import DateTimeWidget


class TimeslotForm(forms.Form):
    start = forms.DateTimeField(label='Start Time', help_text=mark_safe('Format: MM/DD/YYYY HH:MM:SS <br />Example: 10/14/2007 14:00:00'), widget=DateTimeWidget)
    hours = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    minutes = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    description = forms.CharField(widget=forms.TextInput(attrs={'size':'100'}), required = False)

    def save_timeslot(self, program, slot, type):
        slot.start = self.cleaned_data['start']
        slot.end = slot.start + timedelta(hours=self.cleaned_data['hours'], minutes=self.cleaned_data['minutes'])

        if type == "training":
            slot.event_type = EventType.get_from_desc('Teacher Training')
        elif type == "interview":
            slot.event_type = EventType.get_from_desc('Teacher Interview')
        else:
            slot.event_type = EventType.get_from_desc("Class Time Block") # default event type

        slot.program = program
        slot.short_description = slot.start.strftime('%A, %B %d %Y %I:%M %p') + " to " + slot.end.strftime('%I:%M %p')
        if not self.cleaned_data['description']:
            slot.description = slot.short_description
        else:
            slot.description = self.cleaned_data['description']

        slot.save()

