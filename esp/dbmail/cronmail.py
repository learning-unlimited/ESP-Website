from esp.cal.models import Event
from esp.dbmail.models import MessageRequest, EmailRequest
from esp.dbmail.controllers import EmailController
from esp.users.models import UserBit
from esp.datatree.models import GetNode
from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth.models import User, AnonymousUser
from esp.users.models import ESPUser
from esp.miniblog.models import Entry
from django.core.mail import send_mail

from django.conf import settings
import time

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

def send_miniblog_messages():
    entries = Entry.objects.filter(email = True, sent = False)
    verb = GetNode('V/Subscribe')
    if hasattr(settings, 'EMAILTIMEOUT') and settings.EMAILTIMEOUT is not None:
        wait = settings.EMAILTIMEOUT
    else:
        wait = 1.5
        
    for entry in entries:
        if entry.fromuser is None or type(entry.fromuser) == AnonymousUser:
            fromemail = 'esp@mit.edu'
        else:
            fromemail = '%s <%s>' % (ESPUser(entry.fromuser).name(),
                                     entry.fromuser.email)
        emails = {}
        bits = UserBit.bits_get_users(qsc = entry.anchor, verb = verb)
        for bit in bits:
            emails[bit.user.email] = ESPUser(bit.user).name()
        for email,name in emails.items():
            send_mail(entry.title,
                      entry.content,
                      fromemail,
                      ['%s <%s>' % (name, email)],
                      True)
            print "Sent mail to %s" % (name)
            time.sleep(wait)
        entry.sent = True
        entry.save()
