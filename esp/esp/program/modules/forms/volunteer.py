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
  Email: web-team@learningu.org
"""

from django import forms
from django.utils.safestring import mark_safe
from django.db.models import Count
from esp.cal.models import Event, EventType
from esp.program.models import VolunteerRequest, VolunteerOffer
from esp.utils.widgets import DateTimeWidget, DateWidget
from localflavor.us.forms import USPhoneNumberField
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.program.models import Program

class VolunteerRequestForm(forms.Form):

    vr_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    start_time = forms.DateTimeField(help_text="Enter a time in the form DD/MM/YYYY hh:mm.", widget=DateTimeWidget)
    end_time = forms.DateTimeField(help_text="Enter a time in the form DD/MM/YYYY hh:mm.", widget=DateTimeWidget)
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
            ts.program = self.program
            ts.start = self.cleaned_data['start_time']
            ts.end = self.cleaned_data['end_time']
            ts.short_description = ts.description = self.cleaned_data['description']
            ts.event_type = EventType.get_from_desc('Volunteer')
            ts.save()
            vr = VolunteerRequest()
            vr.program = self.program
            vr.timeslot = ts
            vr.num_volunteers = self.cleaned_data['num_volunteers']
            vr.save()


class VolunteerOfferForm(forms.Form):
    user = forms.IntegerField(required=False, widget=forms.HiddenInput)

    name = forms.CharField(max_length=80, label='Your Name')
    email = forms.EmailField(label='Email address')
    phone = USPhoneNumberField(label='Phone number')

    shirt_size = forms.ChoiceField(choices=[], required=False)
    shirt_type = forms.ChoiceField(choices=[], required=False)

    requests = forms.MultipleChoiceField(choices=(), label='Timeslots', help_text="Sign up for one or more shifts; remember to avoid conflicts with your classes if you're teaching!", widget=forms.CheckboxSelectMultiple, required=False)
    has_previous_requests = forms.BooleanField(widget=forms.HiddenInput, required=False, initial=False)
    clear_requests = forms.BooleanField(widget=forms.HiddenInput, required=False, initial=False)

    comments = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'cols': 60}), help_text='Any comments or special circumstances you would like us to know about?', required=False)

    confirm = forms.BooleanField(help_text=mark_safe('<span style="color: red; font-weight: bold;">I agree to show up at the time(s) selected above.</span>'), required=False)

    def __init__(self, *args, **kwargs):
        def positive_or_no(n):
            return (n > 0) and ('%d' % n) or 'no'

        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to VolunteerOfferForm')

        super(VolunteerOfferForm, self).__init__(*args, **kwargs)
        vrs = self.program.getVolunteerRequests()
        self.fields['requests'].choices = [(v.id, '%s: %s (%s more needed)' % (v.timeslot.pretty_time(), v.timeslot.description, positive_or_no(v.num_volunteers - v.num_offers()))) for v in vrs]
        self.fields['shirt_size'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('volunteer_shirt_sizes').split(',')]
        self.fields['shirt_type'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('shirt_types').split(',')]

        #   Show t-shirt fields if specified by Tag (disabled by default)
        if not Tag.getBooleanTag('volunteer_tshirt_options'):
            del self.fields['shirt_size']
            del self.fields['shirt_type']
        elif not Tag.getBooleanTag('volunteer_tshirt_type_selection'):
            del self.fields['shirt_type']

        if not Tag.getBooleanTag('volunteer_allow_comments'):
            del self.fields['comments']
        else:
            tag_data = Tag.getProgramTag('volunteer_help_text_comments', self.program)
            if tag_data:
                self.fields['comments'].help_text = tag_data

    def load(self, user):
        self.fields['user'].initial = user.id
        self.fields['email'].initial = user.email
        self.fields['name'].initial = user.name()
        if user.getLastProfile().contact_user:
            self.fields['phone'].initial = user.getLastProfile().contact_user.phone_cell

        previous_offers = user.getVolunteerOffers(self.program).order_by('-id')
        if previous_offers.exists():
            self.fields['has_previous_requests'].initial = True
            self.fields['requests'].initial = list(previous_offers.values_list('request', flat=True))
            if 'shirt_size' in self.fields:
                self.fields['shirt_size'].initial = previous_offers[0].shirt_size
            if 'shirt_type' in self.fields:
                self.fields['shirt_type'].initial = previous_offers[0].shirt_type
            if 'comments' in self.fields:
                self.fields['comments'].initial = previous_offers[0].comments

    def save(self):
        #   Reset user's offers
        if self.cleaned_data['user']:
            user = ESPUser.objects.get(id=self.cleaned_data['user'])
            user.volunteeroffer_set.all().delete()

        if self.cleaned_data.get('clear_requests', False):
            #   They want to cancel all shifts - don't do anything further.
            return []

        #   Create user if one doesn't already exist, otherwise associate a user.
        #   Note that this will create a new user account if they enter an email
        #   address different from the one on file.
        if not self.cleaned_data['user']:
            user_data = {'first_name': self.cleaned_data['name'].split()[0],
                         'last_name': ' '.join(self.cleaned_data['name'].split()[1:]),
                         'email': self.cleaned_data['email'],
                        }
            existing_users = ESPUser.objects.filter(**user_data).order_by('-id')
            if existing_users.exists():
                #   Arbitrarily pick the most recent account
                #   This is not too important, we just need a link to an email address.
                user = existing_users[0]
            else:
                auto_username = ESPUser.get_unused_username(user_data['first_name'], user_data['last_name'])
                user = ESPUser.objects.create_user(auto_username, user_data['email'])
                user.__dict__.update(user_data)
                user.save()
                #   Send them an email so they can set their password
                user.recoverPassword()

        #   Record this user account as a volunteer
        user.makeVolunteer()

        #   Remove offers with the same exact contact info
        VolunteerOffer.objects.filter(email=self.cleaned_data['email'], phone=self.cleaned_data['phone'], name=self.cleaned_data['name']).delete()

        offer_list = []
        for req in self.cleaned_data['requests']:
            o = VolunteerOffer()
            o.user_id = user.id
            o.email = self.cleaned_data['email']
            o.phone = self.cleaned_data['phone']
            o.name = self.cleaned_data['name']
            o.confirmed = self.cleaned_data['confirm']
            if 'shirt_size' in self.cleaned_data:
                o.shirt_size = self.cleaned_data['shirt_size']
            if 'shirt_type' in self.cleaned_data:
                o.shirt_type = self.cleaned_data['shirt_type']
            if 'comments' in self.cleaned_data:
                o.comments = self.cleaned_data['comments']
            o.request_id = req
            o.save()
            offer_list.append(o)
        return offer_list

    def clean(self):
        """ Does more thorough validation since to allow flexibility, all of the form fields
            now have required=False.    """

        #   If the hidden field clear_requests is True, that means the user confirmed that
        #   they want to cancel all of their volunteer shifts; skip further validation.
        if not self.cleaned_data.get('clear_requests', False):
            #   Having no shifts selected causes a different error message depending
            #   on whether the user had existing shifts.
            if len(self.cleaned_data.get('requests', [])) == 0:
                if self.cleaned_data.get('has_previous_requests', False):
                    raise forms.ValidationError('Error: You must click "Confirm" in the pop-up dialog to remove all of your previous requests.')
                else:
                    raise forms.ValidationError('You did not select any volunteer shifts.')
            #   All changes must be accompanied by the confirmation checkbox.
            if 'confirm' in self.cleaned_data and not self.cleaned_data['confirm']:
                raise forms.ValidationError('Please confirm that you will show up to volunteer at the times you selected.')
        return self.cleaned_data

class VolunteerImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)
    start_date = forms.DateField(label='First Day of New Program', widget=DateWidget)

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(VolunteerImportForm, self).__init__(*args, **kwargs)
        qs = Program.objects.annotate(vr_count = Count('volunteerrequest')).filter(vr_count__gt=0)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs
