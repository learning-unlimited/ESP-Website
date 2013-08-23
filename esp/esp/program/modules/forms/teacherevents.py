from django import forms

from datetime import timedelta

from esp.resources.models import ResourceType, Resource, ResourceAssignment
from esp.cal.models import EventType, Event
from esp.program.models import Program
from esp.utils.widgets import DateTimeWidget

class TimeslotForm(forms.Form):
    start = forms.DateTimeField(label='Start Time', help_text='Format: MM/DD/YYYY HH:MM:SS <br />Example: 10/14/2007 14:00:00', widget=DateTimeWidget)
    hours = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))
    minutes = forms.IntegerField(widget=forms.TextInput(attrs={'size':'6'}))

    def save_timeslot(self, program, slot, type):
        slot.start = self.cleaned_data['start']
        slot.end = slot.start + timedelta(hours=self.cleaned_data['hours'], minutes=self.cleaned_data['minutes'])

        if type == "training":
            slot.event_type = EventType.objects.get_or_create(description='Teacher Training')[0]
        elif type == "interview":
            slot.event_type = EventType.objects.get_or_create(description='Teacher Interview')[0]
        else:
            slot.event_type = EventType.objects.all()[0] # default event type

        slot.program = program
        slot.short_description = slot.start.strftime('%A, %B %d %Y %I:%M %p') + " to " + slot.end.strftime('%I:%M %p')
        slot.description = slot.short_description
        
        slot.save()

