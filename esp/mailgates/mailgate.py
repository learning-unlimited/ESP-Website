#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

from __future__ import absolute_import
from __future__ import print_function
import sys, os, email, hashlib, re, smtplib, socket, random
from io import open
new_path = '/'.join(sys.path[0].split('/')[:-1])
sys.path += [new_path]
sys.path.insert(0, "/usr/sbin/")
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import logging
# Make sure we end up in our logger even though this file is outside esp/esp/
logger = logging.getLogger('esp.mailgate')

import os.path
project = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Path for site code
sys.path.insert(0, project)

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

import django
django.setup()
from esp.dbmail.models import EmailList, send_mail
from django.conf import settings

import_location = 'esp.dbmail.receivers.'
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
ORGANIZATION_NAME = settings.INSTITUTION_NAME + '_' + settings.ORGANIZATION_SHORT_NAME

#DEBUG=True
DEBUG=False

user = "UNKNOWN USER"

try:
    user = os.environ['LOCAL_PART']

    message = email.message_from_file(sys.stdin)

    handlers = EmailList.objects.all()

    for handler in handlers:
        re_obj = re.compile(handler.regex)
        match = re_obj.search(user)


        if not match: continue

        Class = getattr(__import__(import_location + handler.handler.lower(), (), (), ['']), handler.handler)

        instance = Class(handler, message)

        instance.process(user, *match.groups(), **match.groupdict())

        if not instance.send:
            continue

        # Catch sender's message and grab the data fields (To, From, Subject, Body, etc.)
        data = dict()
        for field in ['to', 'from', 'cc', 'bcc', 'subject', 'body', 'attachments']:
            if field == 'to':
                data[field] = [x for x in instance.recipients.split(',') if not x.endswith(settings.EMAIL_HOST_SENDER)]
            else:
                data[field] = message[field].split(',')

       # If the sender's email is not associated with an account on the site,
       # do not forward the email 
       if not data['from']:
           continue
       else:
           users = ESPUser.objects.filter(email=data['from']).order_by('date_joined') # sort by oldest to newest
           if len(users) == 0:
               logger.warning('Received email from {}, which is not associated with a user'.format(data['from'])
               # TODO: send the user a bounce message but limit to one bounce message per day/week/something using
               # something similar to dbmail.MessageRequests to keep track
               continue
           elif len(users) == 1:
               sender = users[0]
           # If there is more than one associated account, choose one by prefering admin > teacher > volunteer >
           # student then choosing the earliest account created. Then send as before using the unique account.
           elif len(users) > 1:
               for group_name in ['Administrator', 'Teacher', 'Volunteer', 'Student', 'Educator']
                   group_users = [x for x in users if len(x.groups.filter(name=group_name)) > 0]
                   if len(group_users) > 0:
                       sender = group_users[0] # choose the first (oldest) account if there is still more than
                       # one; it won't matter because they all go to the same email by construction
                       break
               finally: # if the users aren't in any of the standard groups above, ...
                   sender = users[0] # ... then just pick the oldest account created by selecting users[0] as above
           else:
               logger.error('Negative number of possible senders in supposed list `{}`. Skipping....'.format(users))
               continue
           # Having identified the sender, if the sender's email is associated with an account on the website,
           # use SendGrid to send an email to each recipient of the original message (To, Cc, Bcc) individually from
           # the sender's site email
           logger.info('Sending email as {}'.format(sender))
           for recipient in data['to'] + data['cc'] + data['bcc']:
               send_mail(subject=data['subject'], message=data['body'],
                         from_email='{}@{}'.format(users[0], settings.EMAIL_HOST_SENDER),
                         recipient_list=[recipient], fail_silently=False)
           del sender, recipient, users
        sys.exit(0)


except Exception as e:
    # we dont' want to care if it's an exit
    if isinstance(e, SystemExit):
        raise

    if DEBUG:
        raise
    else:
        logger.warning("Couldn't find user '%s'", user)
        print("""
%s MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email %s.

""" % (ORGANIZATION_NAME, user, SUPPORT))
        sys.exit(1)
