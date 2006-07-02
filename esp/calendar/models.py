from django.db import models
from esp.watchlists.models import Datatree, DatatreeNodeData
from esp.dbmail.models import MessageRequest
from esp.workflow.models import Controller, ControllerDB
from datetime import datetime

# Create your models here.

class EventType(models.Model):
    """ A list of possible event types, ie. Program, Social Activity, etc. """
    description = models.TextField() # Textual description; not computer-parseable

class Series(models.Model):
    """ A container object for grouping Events.  Can be nested. """
    description = models.TextField()
    parent = models.ForeignKey('self', blank=True, null=True)

    def is_happening(self, time=datetime.now()):
        """ Returns True if any Event contained by this Series, or any event contained by any Series nested beneath this Series, returns is_happening(time)==True """
        for event in self.event_set.all():
            if event.is_happening(time):
                return True

        for series in self.series_set.all():
            if series.is_happening(time):
                return True;

        return False;

class Event(models.Model):
    """ A unit calendar entry.

    All calendar entries are events; all data for the event that doesn't fit into the event field is keyed in from a remote class. """
    start = models.DateTimeField() # Event start time
    end = models.DateTimeField() # Event end time
    description = models.TextField() # Event textual description; not computer-parseable
    event_type = models.ForeignKey(EventType) # The tyoe of event.  This implies, though does not require, the types of data that are keyed to this event.
    container_series = models.ForeignKey(Series, blank=True, null=True)

    def is_happening(self, time=datetime.now()):
        """ Return True if the specified time is between start and end """
        return (time > start and time < end)
    
class Program(models.Model):
    """ An ESP program, ie. HSSP, Splash, etc. """
    event = models.OneToOneField(Event)

class CalendarHook(models.Model):
    """ A hook that binds an arbitrary controller to the start of an event """
    controller = models.ForeignKey(ControllerDB) # The controller to activate
    # <UglyHack> <!-- The following expression has to be evaluated directly by eval()!!!  This is a hideous, massive, blatant security hole!!!  There has to be a better way to do this...
    query = models.TextField() # The query that, when executed, gets the QuerySet for the controller.  I don't know of a way to get a QuerySet into a database table.
    # </UglyHack>
    event = models.ForeignKey(Event) # The event to trigger off of
    trigger_time = models.DateTimeField(blank=True, null=True, default=None) # The time to trigger the specified event.  If null, trigger at the start time of the associated Event instance.

class EmailReminder(models.Model):
    """ A reminder, associated with an Event, that is to be sent by e-mail """
    event = models.ForeignKey(Event)
    email = models.ForeignKey(MessageRequest)
    date_to_send = models.DateTimeField()
    sent = models.BooleanField(default=True)


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

