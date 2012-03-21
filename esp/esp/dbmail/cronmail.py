
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
import time

from esp.cal.models import Event
from esp.dbmail.models import MessageRequest, EmailRequest, send_mail, TextOfEmail
from esp.dbmail.controllers import EmailController
from esp.users.models import UserBit
from esp.datatree.models import *
from datetime import datetime, timedelta
from django.db.models.query import Q
from django.contrib.auth.models import User, AnonymousUser
from django.db import transaction
from esp.users.models import ESPUser
from esp.miniblog.models import Entry

from django.conf import settings

import os

@transaction.autocommit
def process_messages():
    """ Go through all unprocessed messages and process them. """
    
    #   Perform an atomic update in order to claim which messages we will be processing.
    my_pid = os.getpid()
    now = datetime.now()
    target_time = now + timedelta(seconds=10)
    MessageRequest.objects.filter(Q(processed_by__lte=now) | Q(processed_by__isnull=True)).filter(processed=False).update(processed_by=target_time)
    
    #   Identify the messages we just claimed.
    messages = MessageRequest.objects.filter(processed_by=target_time, processed=False)

    #   Process message requests
    for message in messages:
        try:
            message.process(True)
        except:
            message.processed_by = None
            message.save()
        else:
            message.processed = True
            message.save()
    return list(messages)

@transaction.autocommit
def send_email_requests(messages):
    """ Go through all email requests that aren't sent and send them. """
    
    #   Find e-mail requests only for the specified messages.
    mailtxts = TextOfEmail.objects.filter(Q(sent_by__lte=datetime.now()) |
                                          Q(sent_by__isnull=True),
                                          sent__isnull=True,
                                          emailrequest__msgreq__in=messages)
    mailtxts_list = list(mailtxts)
    
    #   Update these TextOfEmails so we won't try to send them ever again
    mailtxts.update(sent_by = datetime.now() + timedelta(seconds=10))
    
    if hasattr(settings, 'EMAILTIMEOUT') and settings.EMAILTIMEOUT is not None:
        wait = settings.EMAILTIMEOUT
    else:
        wait = 1.5
    
    num_sent = 0
    for mailtxt in mailtxts_list:
        try:
            mailtxt.send()
        except:
            #   Raise an exception if sending failed - we want to find out what happened.
            mailtxt.sent_by = None
            mailtxt.save()
            raise
        else:
            mailtxt.sent = datetime.now()
            mailtxt.save()
            num_sent += 1

        time.sleep(wait)
    if num_sent > 0:
        print 'Sent %d messages' % num_sent
    
@transaction.autocommit
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

@transaction.autocommit
def send_miniblog_messages():
    entries = Entry.objects.filter(email = True, sent = False)


    for entry in entries:
        entry.sent = True
        entry.save()

    verb = GetNode('V/Subscribe')
    if hasattr(settings, 'EMAILTIMEOUT') and settings.EMAILTIMEOUT is not None:
        wait = settings.EMAILTIMEOUT
    else:
        wait = 1.5

    for entry in entries:
        if entry.fromemail is None or len(entry.fromemail.strip()) == 0:
            if entry.fromuser is None or type(entry.fromuser) == AnonymousUser:
                fromemail = 'esp@mit.edu'
            else:
                fromemail = '%s <%s>' % (ESPUser(entry.fromuser).name(),
                                         entry.fromuser.email)
        else:
            fromemail = entry.fromemail

        emails = {}
        bits = UserBit.bits_get_users(qsc = entry.anchor, verb = verb)
        for bit in bits:
            if bit.user is None or type(bit.user) == AnonymousUser:
#                print "Error with %s (%s)" % (str(entry), str(bit.user))
                pass
            else:
                emails[bit.user.email] = ESPUser(bit.user).name()
                
        for email,name in emails.items():
            send_mail(entry.title,

                      entry.content,
                      fromemail,
                      ['%s <%s>' % (name, email)],
                      True)
            print "Sent mail to %s" % (name)
            time.sleep(wait)



