
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
  Email: web-team@learningu.org
"""
import logging
logger = logging.getLogger(__name__)

from django.db import models
from datetime import datetime, timedelta
from argcache import cache_function

# Create your models here.

class EventType(models.Model):
    """ A list of possible event types, ie. Program, Social Activity, etc. """
    description = models.TextField() # Textual description; not computer-parseable

    def __unicode__(self):
        return unicode(self.description)

    @cache_function
    def get_from_desc(cls, desc):
        """ A cached function for getting EventTypes that we know must exist
        if someone has run install() """
        return EventType.objects.get(description=desc)
    get_from_desc.depend_on_model('cal.EventType')
    get_from_desc = classmethod(get_from_desc)

class Event(models.Model):
    """ A unit calendar entry.

    All calendar entries are events; all data for the event that doesn't fit into the event field is keyed in from a remote class. """
    start = models.DateTimeField() # Event start time
    end = models.DateTimeField() # Event end time
    short_description = models.TextField() # Event short description
    description = models.TextField() # Event textual description; not computer-parseable
    name = models.CharField(max_length=80)
    program = models.ForeignKey('program.Program',blank=True, null=True)
    event_type = models.ForeignKey(EventType) # The type of event.  This implies, though does not require, the types of data that are keyed to this event.
    priority = models.IntegerField(blank=True, null=True) # Priority of this event

    def title(self):
        return self.name

    def duration(self):
        # Matches the rounding of class/section durations
        dur = self.end - self.start
        hrs = round(dur.total_seconds() / 3600.0, 2)
        return timedelta(hours = hrs)

    def start_w_buffer(self, buffer = timedelta(minutes=15)):
        #Adds a buffer to the start time
        return self.start - buffer

    def end_w_buffer(self, buffer = timedelta(minutes=15)):
        #Adds a buffer to the start time
        return self.end + buffer

    def duration_str(self):
        dur = self.end - self.start
        hours = int(dur.seconds / 3600)
        minutes = int(dur.seconds / 60) - hours * 60
        return u'%d hr %d min' % (hours, minutes)

    def __unicode__(self):
        return self.start.strftime('%a %b %d: ').decode('utf-8') + self.short_time()

    def short_time(self):
        day_list = [u'Mon', u'Tue', u'Wed', u'Thu', u'Fri', u'Sat', u'Sun']

        start_minutes = u''
        end_minutes = u''
        start_ampm = u''
        if self.start.minute != 0:
            start_minutes = u':%02d' % self.start.minute
        if self.end.minute != 0:
            end_minutes = u':%02d' % self.end.minute
        if (self.start.hour < 12) != (self.end.hour < 12):
            start_ampm = self.start.strftime(' %p').decode('utf-8')

        return u'%d%s%s to %d%s %s' % ( (self.start.hour % 12) or 12, start_minutes, start_ampm,
            (self.end.hour % 12) or 12, end_minutes, self.end.strftime('%p').decode('utf-8') )

    @staticmethod
    def total_length(event_list):
        #   Returns the time from the start of the first event to the end of the last.
        event_list = list(event_list)
        event_list.sort(key=lambda x:x.start)
        if len(event_list) > 0:
            # Matches the rounding of class/section durations
            dur = event_list[-1].end - event_list[0].start
            hrs = round(dur.total_seconds() / 3600.0, 2)
            return timedelta(hours = hrs)
        else:
            return timedelta(seconds=0)

    @staticmethod
    def collapse(eventList, tol=timedelta(minutes=1)):
        """ this method will return a list of new collapsed events """
        from copy import copy
        sortedList = copy(eventList)
        sortedList.sort()

        for i in range(1,len(sortedList)):
            if (sortedList[i-1].end+tol) >= sortedList[i].start:
                sortedList[i]   = Event(start=sortedList[i-1].start, end=sortedList[i].end)
                sortedList[i-1] = None

        newList = [ x for x in sortedList if x != None ]

        return newList

    @staticmethod
    def contiguous(event1, event2):
        """ Returns true if the second argument is less than 20 minutes apart from the first one. """
        tol = timedelta(minutes=20)

        if (event2.start - event1.end) < tol:
            return True
        else:
            return False

    @staticmethod
    def group_contiguous(event_list):
        """ Takes a list of events and returns a list of lists where each sublist is a contiguous group. """
        from copy import copy
        sorted_list = copy(event_list)
        sorted_list.sort()

        grouped_list = []
        current_group = []
        last_event = None

        for event in sorted_list:

            if last_event is None or Event.contiguous(last_event, event):
                current_group.append(event)
            else:
                grouped_list.append(copy(current_group))
                current_group = [event]

            last_event = event

        if len(current_group) > 0:
            grouped_list.append(current_group)

        return grouped_list

    def pretty_time(self, include_date = False): # if include_date is True, display the date as well (e.g., display "Sun, July 10" instead of just "Sun")
        s = self.start.strftime('%a').decode('utf-8')
        s2 = self.end.strftime('%a').decode('utf-8')
        # The two days of the week are different
        if include_date:
            s += self.start.strftime(', %b %d,').decode('utf-8')
            s2 += self.end.strftime(', %b %d,').decode('utf-8')
        if s != s2:
            return s + u' ' + self.start.strftime('%I:%M%p').lower().strip('0').decode('utf-8') + u'--' \
               + s2 + u' ' + self.end.strftime('%I:%M%p').lower().strip('0').decode('utf-8')
        else:
            return s + u' ' + self.start.strftime('%I:%M%p').lower().strip('0').decode('utf-8') + u'--' \
               + self.end.strftime('%I:%M%p').lower().strip('0').decode('utf-8')

    def pretty_time_with_date(self):
        return self.pretty_time(include_date = True)

    def pretty_date(self):
        return self.start.strftime('%A, %B %d').decode('utf-8')

    def pretty_start_time(self):
        return self.start.strftime('%a').decode('utf-8') + u' ' + self.start.strftime('%I:%M%p').lower().strip('0').decode('utf-8')

    def parent_program(self):
        return self.program

    def __cmp__(self, other):
        try:
            return cmp(self.start, other.start)
        except:
            return 0

def install():
    """
    This ensures the existence of certain event types:
        Class Time Block -- for classes, obviously
        Open Class Time Block -- for open classes, when not scheduling them in normal timeblocks
        Teacher Interview -- for TeacherEventsModule
        Teacher Training -- for TeacherEventsModule
    """
    logger.info("Installing esp.cal initial data...")
    for x in [ 'Class Time Block', 'Open Class Time Block', 'Teacher Interview', 'Teacher Training', 'Compulsory', 'Volunteer']:
        if not EventType.objects.filter(description=x).exists():
            EventType.objects.create(description=x)
