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
from esp.users.models import ESPUser
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
            logger.debug("Instance did not send")
            continue

        # Catch sender's message and grab the data fields (To, From, Subject, Body, etc.)
        data = dict()
        for field in ['to', 'from', 'cc', 'bcc', 'subject', 'body', 'attachments']:
            if field == 'to':
                # TODO: in the long term, it would be better to implement polymorphism so that class lists and individual user aliases both have `recipients`
                if hasattr(instance, 'recipients'):
                    data[field] = [x for x in instance.recipients if not x.endswith(settings.EMAIL_HOST_SENDER)] # TODO: make sure to expand the `to` field as needed so sendgrid doesn't just forward in a loop
                elif hasattr(instance, 'message'):
                    data[field] = instance.message['to']
                else:
                    raise TypeError("Unknown receiver type for `{}`".format(instance))

            else:
                if message[field] is None:
                    data[field] = ''
                elif field in ['subject', 'body', 'attachments']:
                    data[field] = message[field]
                else:
                    data[field] = message[field].split(',')


       # If the sender's email is not associated with an account on the site,
       # do not forward the email
        if not data['from']:
            logger.debug(f"User has no account: `from` field is `{data['from']}`")
            continue
        else:
            if len(data['from']) != 1:
                raise AttributeError(f"More than one sender: `{data['from']}`")
            email_address = data['from'][0].split('<')[1].split('>')[0]
            users = ESPUser.objects.filter(email=email_address).order_by('date_joined') # sort oldest to newest
            if len(users) == 0:
                logger.warning('Received email from {}, which is not associated with a user'.format(data['from']))
                # TODO: send the user a bounce message but limit to one bounce message per day/week/something using
                # something similar to dbmail.MessageRequests to keep track
                continue
            elif len(users) == 1:
                sender = users[0]
            # If there is more than one associated account, choose one by prefering admin > teacher > volunteer >
            # student then choosing the earliest account created. Then send as before using the unique account.
            elif len(users) > 1:
                for group_name in ['Administrator', 'Teacher', 'Volunteer', 'Student', 'Educator']:
                    group_users = [x for x in users if len(x.groups.filter(name=group_name)) > 0]
                    if len(group_users) > 0:
                        sender = group_users[0] # choose the first (oldest) account if there is still more than
                        # one; it won't matter because they all go to the same email by construction
                        break
                else: # if the users aren't in any of the standard groups above, ...
                    sender = users[0] # ... then just pick the oldest account created by selecting users[0] as above
                logger.debug(f"Group selection: {group_name} -> {group_users}")
            else:
                logger.error('Negative number of possible senders in supposed list `{}`. Skipping....'.format(users))
                continue
            # Having identified the sender, if the sender's email is associated with an account on the website,
            # use SendGrid to send an email to each recipient of the original message (To, Cc, Bcc) individually from
            # the sender's site email
            logger.info('Sending email as {}'.format(sender))
            # TODO: to avoid loops, remove any @site.learningu.org addresses? There's probably a better way
            if isinstance(data['to'], str):
                data['to'] = [data['to']]
            for recipient in data['to']: # + data['cc'] + data['bcc']:
                logger.debug(f"Sending to `{recipient}`")
                send_mail(subject=data['subject'], message=data['body'],
                         from_email='{}@{}'.format(sender, settings.EMAIL_HOST_SENDER),
                          recipient_list=[recipient], fail_silently=False)
            del sender, recipient, users
        sys.exit(0)


except Exception as e:
    # we don't want to care if it's an exit
    if isinstance(e, SystemExit):
        raise

    if DEBUG:
        raise
    else:
        logger.warning("On user '{}', got error `{}`".format(user, e))

        print("""
%s MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email %s.

""" % (ORGANIZATION_NAME, user, SUPPORT))
        sys.exit(1)
