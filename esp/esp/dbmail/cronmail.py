
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
import time

from esp.dbmail.models import MessageRequest, send_mail, TextOfEmail
from datetime import datetime, timedelta
from django.db.models.query import Q
from django.db import transaction
from django.template.loader import render_to_string

from django.conf import settings

import os

@transaction.autocommit
def process_messages(debug=False):
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
            message.process(True, debug=debug)
        except:
            message.processed_by = None
            message.save()
        else:
            message.processed = True
            message.save()
    return list(messages)

@transaction.autocommit
def send_email_requests(debug=False):
    """ Go through all email requests that aren't sent and send them. """

    if hasattr(settings, 'EMAILRETRIES') and settings.EMAILRETRIES is not None:
        retries = settings.EMAILRETRIES
    else:
        retries = 2 # default 3 tries total

    #   Find unsent e-mail requests
    mailtxts = TextOfEmail.objects.filter(Q(sent_by__lte=datetime.now()) |
                                          Q(sent_by__isnull=True),
                                          sent__isnull=True,
                                          locked=False,
                                          tries__lte=retries)
    mailtxts_list = list(mailtxts)
    
    #   Mark these messages as locked for this send_email_requests call
    #   If the process is killed unexpectedly, then any locked messages will need to be unlocked
    #   TODO: consider a lock on the function, for example by locking a file
    mailtxts.update(locked=True)
    
    if hasattr(settings, 'EMAILTIMEOUT') and settings.EMAILTIMEOUT is not None:
        wait = settings.EMAILTIMEOUT
    else:
        wait = 1.5
    
    num_sent = 0
    errors = [] # if any messages failed to deliver

    for mailtxt in mailtxts_list:
        try:
            mailtxt.send(debug=debug)
        except Exception as e:
            #   Increment tries so that we don't continuously attempt to send this message
            mailtxt.tries = mailtxt.tries + 1
            mailtxt.save()

            #   Queue report about this delivery failure
            errors.append({'email': mailtxt, 'exception': str(e)})
            if debug: print "Encountered error while sending to " + str(mailtxt.send_to) + ": " + str(e)
        else:
            num_sent += 1

        time.sleep(wait)

    #   Unlock the messages as we are done processing them
    mailtxts.update(locked=False)

    if num_sent > 0:
        if debug: print 'Sent %d messages' % num_sent

    #   Report any errors
    if errors:
        recipients = [mailtxt.send_from]

        if 'bounces' in settings.DEFAULT_EMAIL_ADDRESSES:
            recipients.append(settings.DEFAULT_EMAIL_ADDRESSES['bounces'])

        mail_context = {'errors': errors}
        delivery_failed_string = render_to_string('email/delivery_failed', mail_context)
        if debug:
            print 'Mail delivery failure'
            print delivery_failed_string
        send_mail('Mail delivery failure', delivery_failed_string, settings.SERVER_EMAIL, recipients)
    elif num_sent > 0:
        if debug: print 'No mail delivery failures'
