__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""

from django import forms
from esp.cal.models import Event, EventType
from esp.program.models import VolunteerRequest, VolunteerOffer
from esp.utils.widgets import DateTimeWidget
from esp.users.forms.user_profile import PhoneNumberField
from esp.users.models import ESPUser

class VolunteerRequestForm(forms.Form):
    
    vr_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    start_time = forms.DateTimeField(widget=DateTimeWidget)
    end_time = forms.DateTimeField(widget=DateTimeWidget)
    num_volunteers = forms.IntegerField(label='Number of volunteers needed')
    description = forms.CharField(max_length=128, help_text='What would volunteers do during this timeslot?  (Examples: Registration, Security)')
    
    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to VolunteerRequestForm')
        super(VolunteerRequestForm, self).__init__(*args, **kwargs)
    
    def load(self, vr):
        self.initial['vr_id'] = vr.id
        self.initial['start_time'] = vr.timeslot.start
        self.initial['end_time'] = vr.timeslot.end
        self.initial['num_volunteers'] = vr.num_volunteers
        self.initial['description'] = vr.timeslot.description

    def save(self, vr=None):
        if vr:
            ts = vr.timeslot
            ts.start = self.cleaned_data['start_time']
            ts.end = self.cleaned_data['end_time']
            ts.short_description = ts.description = self.cleaned_data['description']
            ts.save()
            vr.num_volunteers = self.cleaned_data['num_volunteers']
            vr.program = self.program
            vr.save()
        else:
            ts = Event()
            ts.anchor = self.program.anchor
            ts.start = self.cleaned_data['start_time']
            ts.end = self.cleaned_data['end_time']
            ts.short_description = ts.description = self.cleaned_data['description']
            ts.event_type, created = EventType.objects.get_or_create(description='Volunteer')
            ts.save()
            vr = VolunteerRequest()
            vr.program = self.program
            vr.timeslot = ts
            vr.num_volunteers = self.cleaned_data['num_volunteers']
            vr.save()
            
            
class VolunteerOfferForm(forms.Form):
    user = forms.IntegerField(required=False, widget=forms.HiddenInput)
    
    name = forms.CharField(max_length=80, label='Your Name')
    email = forms.EmailField(label='E-mail address')
    phone = PhoneNumberField(label='Phone number')
    
    requests = forms.MultipleChoiceField(choices=(), label='Timeslots', help_text='Sign up for one or more shifts; remember to avoid conflicts with your classes if you\'re teaching!', widget=forms.CheckboxSelectMultiple)
    
    confirm = forms.BooleanField(help_text='<span style="color: red; font-weight: bold;"> I agree to show up at the time(s) selected above.</span>')
    
    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to VolunteerOfferForm')
    
        super(VolunteerOfferForm, self).__init__(*args, **kwargs)
        vrs = self.program.getVolunteerRequests()
        self.fields['requests'].choices = [(v.id, '%s: %s (%d more needed)' % (v.timeslot.pretty_time(), v.timeslot.description, v.num_volunteers - v.num_offers())) for v in vrs]
    
    def load(self, user):
        user = ESPUser(user)
        print 'Loading %s' % user
        self.fields['user'].initial = user.id
        self.fields['email'].initial = user.email
        self.fields['name'].initial = user.name()
        if user.getLastProfile().contact_user:
            self.fields['phone'].initial = user.getLastProfile().contact_user.phone_cell
        self.fields['requests'].initial = user.getVolunteerOffers(self.program).values_list('request', flat=True)
        print 'Offers: %s' % user.getVolunteerOffers(self.program).values_list('request', flat=True)

    def save(self):
        #   Reset user's offers
        if self.cleaned_data['user']:
            user = ESPUser.objects.get(id=self.cleaned_data['user'])
            user.volunteeroffer_set.all().delete()
        
        #   Remove offers with the same exact contact info
        VolunteerOffer.objects.filter(email=self.cleaned_data['email'], phone=self.cleaned_data['phone'], name=self.cleaned_data['name']).delete()
        
        offer_list = []
        for req in self.cleaned_data['requests']:
            o = VolunteerOffer()
            if 'user' in self.cleaned_data:
                o.user_id = self.cleaned_data['user']
            o.email = self.cleaned_data['email']
            o.phone = self.cleaned_data['phone']
            o.name = self.cleaned_data['name']
            o.confirmed = self.cleaned_data['confirm']
            o.request_id = req
            o.save()
            offer_list.append(o)
        return offer_list
            
    def clean(self):
        if 'confirm' in self.cleaned_data and not self.cleaned_data['confirm']:
            raise forms.ValidationError('Please confirm that you will show up to volunteer at the times you selected.')
        return self.cleaned_data
