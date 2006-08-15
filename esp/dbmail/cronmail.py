from esp.calendar.models import Event
from esp.dbmail.models import MessageRequest, EmailRequest
from esp.dbmail.controllers import EmailController
from esp.users.models import UserBit
from esp.datatree.models import GetNode
from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth.models import User


def event_to_message(event):
    m = MessageRequest()
    m.subject = "Event Notification"
    m.category = GetNode('Q/Event')
    m.sender = 'esp@mit.edu'
    m.msgtext = 'Event Reminder: ' + event.short_description + '\n\n' + event.description
    m.save()
    return m
    
def user_to_email(message, user):
    req = EmailRequest()

def send_event_notice(event_start, event_end):
    """ Send event reminders for all events, if any fraction of an event occurs in the given time range.  Send to all users who are subscribed to each event. """
    messages = []

    for e in Event.objects.filter(start__lte=event_end, end__gte=event_start):
        m = event_to_message(e)
        messages.append(m)
        
        for u in UserBit.bits_get_users(e.anchor, GetNode('V/Subscribe'), now = e.start, end_of_now = e.end).filter(startdate__lt=e.end, enddate__gt=e.start):
            user_to_email(m, u)

    EmailController().run(messages)        
            

def send_event_notices_for_date(day):
    """ Send event reminders for all events that occur in any part on "day" """
    event_start = datetime(day.year, day.month, day.day, 0)
    event_end = datetime(day.year, day.month, day.day, 0) + timedelta(1)

    send_event_notice(event_start, event_end)

def send_event_notices_for_day(day):
    """ Send event notices for either today or tomorrow
    'day' must be one of "today" or "tomorrow"; otherwise "today" is assumed """
    
    if day == 'tomorrow':
        send_event_notices_for_date(datetime.now()+timedelta(1))
    else:
        send_event_notices_for_date(datetime.now())
