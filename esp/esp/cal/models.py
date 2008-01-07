
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.db import models
from esp.datatree.models import DataTree
from esp.dbmail.models import MessageRequest
from esp.workflow.models import Controller, ControllerDB
from datetime import datetime, timedelta
from esp.db.fields import AjaxForeignKey


# Create your models here.

class EventType(models.Model):
    """ A list of possible event types, ie. Program, Social Activity, etc. """
    description = models.TextField() # Textual description; not computer-parseable

    def __str__(self):
        return str(self.description)

    class Admin:
        pass

class Series(models.Model):
    """ A container object for grouping Events.  Can be nested. """
    description = models.TextField()
    target = AjaxForeignKey(DataTree) # location for this Series in the datatree

    class Admin:
        pass

    def __str__(self):
        return str(self.description)

    def is_happening(self, time=datetime.now()):
        """ Returns True if any Event contained by this Series, or any event contained by any Series nested beneath this Series, returns is_happening(time)==True """
        for event in self.event_set.all():
            if event.is_happening(time):
                return True

        for series in self.series_set.all():
            if series.is_happening(time):
                return True;

        return False;

    class Meta:
        verbose_name_plural = 'Series'

class Event(models.Model):
    """ A unit calendar entry.

    All calendar entries are events; all data for the event that doesn't fit into the event field is keyed in from a remote class. """
    anchor = AjaxForeignKey(DataTree)

    start = models.DateTimeField() # Event start time
    end = models.DateTimeField() # Event end time
    short_description = models.TextField() # Event short description
    description = models.TextField() # Event textual description; not computer-parseable
    event_type = models.ForeignKey(EventType) # The type of event.  This implies, though does not require, the types of data that are keyed to this event.
    #    container_series = models.ForeignKey(Series, blank=True, null=True)
    priority = models.IntegerField(blank=True, null=True) # Priority of this event

    def duration(self):
        return self.end - self.start
    
    def duration_str(self):
        dur = self.end - self.start
        hours = int(dur.seconds / 3600)
        minutes = int(dur.seconds / 60) - hours * 60
        return '%d hr %d min' % (hours, minutes)
    
    def __str__(self):
        return self.start.strftime('%a %b %d: %I %p') + ' to ' + self.end.strftime('%I %p')

    def short_time(self):
        day_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        start_minutes = ''
        end_minutes = ''
        if self.start.minute != 0:
            start_minutes = ':%d' % self.start.minute
        if self.end.minute != 0:
            end_minutes = ':%d' % self.end.minute
            
        if self.start.hour >= 12 and self.end.hour >= 12:
            return '%s %d%s to %d%s PM' % (day_list[self.start.weekday()], (self.start.hour - 1) % 12 + 1, start_minutes, (self.end.hour - 1) % 12 + 1, end_minutes)
        elif self.start.hour < 12 and self.end.hour >= 12:
            return '%s %d%s AM to %d%s PM' % (day_list[self.start.weekday()], (self.start.hour - 1) % 12 + 1, start_minutes, (self.end.hour - 1) % 12 + 1, end_minutes)
        else:
            return '%s %d%s to %d%s AM' % (day_list[self.start.weekday()], (self.start.hour - 1) % 12 + 1, start_minutes, (self.end.hour - 1) % 12 + 1, end_minutes)

    def is_happening(self, time=datetime.now()):
        """ Return True if the specified time is between start and end """
        return (time > self.start and time < self.end)

    @staticmethod
    def total_length(event_list):
        #   Returns the time from the start of the first event to the end of the last.
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
        """ Returns true if the second argument is less than 15 minutes apart from the first one. """
        tol = timedelta(minutes=15)
        
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

    def pretty_time(self):
        return self.start.strftime('%a') + ' ' + self.start.strftime('%I:%M%p').lower().strip('0') + '--' \
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
        from esp.program.models import Class
        return Class.objects.filter(meeting_times=self).count()
    
    def __cmp__(self, other):
        return cmp(self.start, other.start)

    class Admin:
        pass

class Program(models.Model):
    """ An ESP program, ie. HSSP, Splash, etc. """
    event = models.OneToOneField(Event)

    def __str__(self):
        return str(self.event)

    class Admin:
        pass

class CalendarHook(models.Model):
    """ A hook that binds an arbitrary controller to the start of an event """
    controller = models.ForeignKey(ControllerDB) # The controller to activate
    # <UglyHack> <!-- The following expression has to be evaluated directly by eval()!!!  This is a hideous, massive, blatant security hole!!!  There has to be a better way to do this...
    query = models.TextField() # The query that, when executed, gets the QuerySet for the controller.  I don't know of a way to get a QuerySet into a database table.
    # </UglyHack>
    event = models.ForeignKey(Event) # The event to trigger off of
    trigger_time = models.DateTimeField(blank=True, null=True, default=None) # The time to trigger the specified event.  If null, trigger at the start time of the associated Event instance.

    class Admin:
        pass

class EmailReminder(models.Model):
    """ A reminder, associated with an Event, that is to be sent by e-mail """
    event = models.ForeignKey(Event)
    email = models.ForeignKey(MessageRequest)
    date_to_send = models.DateTimeField()
    sent = models.BooleanField(default=True)

    def __str__(self):
        return str(self.event) + ': ' + str(self.email)

    class Admin:
        pass

class CalendarGenericHook(Controller):
    """ Run all generic hooks whose time has come """

    def get_webmin_user(self): # Stub; should probably return either "Anonymous", or whatever user the Calendar runs as
        return None

    def get_CalendarHooks_to_run(self, time=datetime.now()): # Get all calendar hooks that have not been run, that should have been run by the specified date/time
        return list(CalendarHooks.objects.filter(has_run=False, trigger_time_lt=time)) + list(CalendarHooks.objects.filter(has_run=False, trigger_time=None, event__start_lt=time))

    def run(self, data): # 'data' is the QuerySet of all CalendarHooks whose time has come
        for hook in self.get_CalendarHooks_to_run():
            hook.getController().run(data, self.webmin_user)
                                            

## class EmailSender(Controller):
##     """ Send all EmailReminders that should have already been sent """
##     def run(self, data, user):
##         for msg in data:


