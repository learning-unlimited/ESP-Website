
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
from esp.cal.models import Event
from esp.web.util import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.forms import ModelForm


class EventForm(ModelForm):
    class Meta:
        model = Event

def createevent(request):
    """ Create an Event, via a Web form """
    
    # If we're POSTed to, we're trying to receive an update
    if request.method == 'POST':
        f = EventForm(request.POST)
        if f.is_valid():
            new_event = f.save()
            return HttpResponseRedirect('/events/edit/?%i', new_event.id)

    # Otherwise, generate a blank new-page form
    else:
        f = EventForm()
    
	return render_to_response('events/create_update', request, GetNode('Q/Web'), {'form': f } )


def updateevent(request, id=None):
    """ Update an Event, via a Web form """
    # aseering 8-9-2006: Code blatantly copied from myesp_createevnt; see that function for reference
    
    # We don't have a generic list page yet; work on that
    if id == None:
        raise Http404
    
    # Because we're lazy like that.
    return createevent(request)


def iCalFeed(request):
    """ Creates an iCal calendar file based on the Events table """
    cal = Calendar()
    cal.add('version', '2.0')

    for e in Event.objects.all():
        cal_event = CalEvent()
        cal_event.add('summary', e.short_description)
        cal_event.add('description', e.description)
        cal_event.add('dtstart', e.start)
        cal_event.add('dtend', e.end)
        cal.add_component(cal_event)

    return cal.as_string()

