
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
from django.db import models
from esp.datatree.models import *
from datetime import datetime, timedelta
from esp.db.fields import AjaxForeignKey
from esp.cache import cache_function

# Create your models here.

class EventType(models.Model):
    """ A list of possible event types, ie. Program, Social Activity, etc. """
    description = models.TextField() # Textual description; not computer-parseable

    def __unicode__(self):
        return unicode(self.description)

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
        if self.program is not None:
            return "%s for %s" % (self.name, self.program.title())
        return self.name

    def duration(self):
        return self.end - self.start
    
    def duration_str(self):
        dur = self.end - self.start
        hours = int(dur.seconds / 3600)
        minutes = int(dur.seconds / 60) - hours * 60
        return '%d hr %d min' % (hours, minutes)
    
    def __unicode__(self):
        return self.start.strftime('%a %b %d: ') + self.short_time()

    def short_time(self):
        day_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        start_minutes = ''
        end_minutes = ''
        start_ampm = ''
        if self.start.minute != 0:
            start_minutes = ':%02d' % self.start.minute
        if self.end.minute != 0:
            end_minutes = ':%02d' % self.end.minute
        if (self.start.hour < 12) != (self.end.hour < 12):
            start_ampm = self.start.strftime(' %p')
        
        return u'%d%s%s to %d%s %s' % ( (self.start.hour % 12) or 12, start_minutes, start_ampm,
            (self.end.hour % 12) or 12, end_minutes, self.end.strftime('%p') )

    def is_happening(self, time=datetime.now()):
        """ Return True if the specified time is between start and end """
        return (time > self.start and time < self.end)

    @staticmethod
    def total_length(event_list):
        #   Returns the time from the start of the first event to the end of the last.
        event_list = list(event_list)
        event_list.sort(key=lambda x:x.start)
        if len(event_list) > 0:
            return event_list[-1].end - event_list[0].start
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
        s = self.start.strftime('%a')
        s2 = self.end.strftime('%a')
        # The two days of the week are different
        if include_date:
            s += self.start.strftime(', %b %d,')
            s2 += self.end.strftime(', %b %d,')
        if s != s2:
            return s + ' ' + self.start.strftime('%I:%M%p').lower().strip('0') + '--' \
               + s2 + ' ' + self.end.strftime('%I:%M%p').lower().strip('0')
        else:
            return s + ' ' + self.start.strftime('%I:%M%p').lower().strip('0') + '--' \
               + self.end.strftime('%I:%M%p').lower().strip('0')
    
    def pretty_date(self):
        return self.start.strftime('%A, %B %d')
    
    def pretty_start_time(self):
        return self.start.strftime('%a') + ' ' + self.start.strftime('%I:%M%p').lower().strip('0')
    
    def num_classes_assigned(self):
        #   Return the number of classes assigned to classrooms in this time slot.
        from esp.resources.models import ResourceAssignment, ResourceType
        classroom = ResourceType.get_or_create('Classroom')
        return ResourceAssignment.objects.filter(resource__event=self, resource__res_type=classroom).count()
    
    def num_classes(self):
        #   Return the number of classes assigned to this time slot.
        from esp.program.models import ClassSection
        return ClassSection.objects.filter(meeting_times=self).count()
    
    def parent_program(self):
        return self.program
    
    def __cmp__(self, other):
        try:
            return cmp(self.start, other.start)
        except:
            return 0
        
class EmailReminder(models.Model):
    """ A reminder, associated with an Event, that is to be sent by e-mail """
    event = models.ForeignKey(Event)
    email = models.ForeignKey('dbmail.MessageRequest')
    date_to_send = models.DateTimeField()
    sent = models.BooleanField(default=True)

    def __unicode__(self):
        return unicode(self.event) + ': ' + unicode(self.email)

def install():
    """
    This ensures the existence of certain event types:
        Class Time Block -- for classes, obviously
        Teacher Interview -- for TeacherEventsModule
        Teacher Training -- for TeacherEventsModule
    """
    for x in [ 'Class Time Block', 'Teacher Interview', 'Teacher Training', 'Compulsory', 'Volunteer' ]:
        EventType.objects.get_or_create(description=x)
