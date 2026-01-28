#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

from __future__ import absolute_import
from __future__ import print_function
import sys, os, base64, email, re, smtplib, socket, random
import itertools
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
from esp.dbmail.models import EmailList, PlainRedirect, send_mail
from esp.users.models import ESPUser
from django.conf import settings
from django.db.models.functions import Lower

import_location = 'esp.dbmail.receivers.'
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
ORGANIZATION_NAME = settings.INSTITUTION_NAME + '_' + settings.ORGANIZATION_SHORT_NAME

#DEBUG=True
DEBUG=False

user = "UNKNOWN USER"


def extract_attachments(msg):
    attachments = []
    for part in msg.iter_attachments():
        filename = part.get_filename()
        content = part.get_payload(decode=True)
        mimetype = part.get_content_type()
        if content:
            attachments.append((filename, content, mimetype))
    return attachments


try:
    user = os.environ['LOCAL_PART']

    message = email.message_from_file(sys.stdin, policy=email.policy.default)

    handlers = EmailList.objects.all()

    for handler in handlers:
        re_obj = re.compile(handler.regex)
        match = re_obj.search(user)


        if not match: continue

        Class = getattr(__import__(import_location + handler.handler.lower(), (), (), ['']), handler.handler)

        instance = Class(handler, message)

        instance.process(user, *match.groups(), **match.groupdict())

        if not instance.send:
            logger.debug("Instance of handler {} with message {} did not send".format(handler, message))
            continue

        # Catch sender's message and grab the data fields (to, from, subject, body, and attachments)
        data = dict()
        # if the instance has a `recipients` attribute, then it is a class list (such as `a123-teachers@`)
        if hasattr(instance, 'recipients'):
            data['to'] = []
            aliases = []
            for recipient in instance.recipients:
                # If the recipient has an email address that does not end with @anysite.learningu.org, keep them
                # TODO: it would be better not to hardcode `.learningu.org` in case we ever change the name, but we
                # only store `thissite.learningu.org` in settings, and we want `anysite.learningu.org` while still
                # allowing user@learningu.org because those resolve to enterprise Gmail addresses
                if recipient.endswith('.learningu.org'):
                    aliases.append(recipient)
                elif '@' in recipient:
                    data['to'].append(recipient)
                else:
                    logger.warning('Email address without `@` symbol: `{}`'.format(recipient))
            redirects = PlainRedirect.objects.annotate(original_lower=Lower("original"
                        )).filter(original_lower__in=[x.split('@')[0].lower() for x in aliases])
            # Split out individual email addresses if any of the redirects is a list
            redirects = list(itertools.chain.from_iterable(map(lambda x: x.destination.split(','), redirects)))
            users = ESPUser.objects.annotate(username_lower=Lower("username"
                    )).filter(username_lower__in=[x.lower() for x in aliases])
            # Grab the emails from the users
            users = [x.email for x in users]
            # Theoretically at least one of these should be empty, but now doesn't seem like the time
            # If the redirect resolve to anything@anysite.learningu.org, kill it
            for address in redirects + users:
                if not address.endswith('.learningu.org'): # TODO: again, would be nice not to hardcode
                    data['to'].append(address)
            # if the above filtering leaves the 'to' list empty, abort
            if len(data['to']) == 0:
                continue
        # if the instance has a `message['to']` attribute, then it is a single address (such as `plain_redirect@` or
        # `username@`)
        elif hasattr(instance, 'message'):
            data['to'] = instance.message['to']
        else:
            raise TypeError("Unknown receiver type for `{}`".format(instance))
        data['from'] = message['from'].split(',') or ''
        data['subject'] = message['subject'] or ''
        # For class lists, grab the code (such as "A123") and prepend it to the subject line
        if hasattr(instance, 'emailcode') and instance.emailcode:
            data['subject'] = '[{}] {}'.format(instance.emailcode, data['subject'])
        if handler.subject_prefix:
            data['subject'] = '[{}] {}'.format(handler.subject_prefix, data['subject'])
        # Put the email body between HTML tags
        data['body'] = '<html>{}</html>'.format(message.get_body(preferencelist=('html', 'plain')).get_content())
        # Use the helper method defined above to get the attachment content
        data['attachments'] = extract_attachments(message)


       # If the sender's email is not associated with an account on the site,
       # do not forward the email
        if not data['from']:
            logger.debug(f"User has no account: `from` field is `{data['from']}`")
            continue
        else:
            if len(data['from']) != 1:
                raise AttributeError(f"More than one sender: `{data['from']}`")
            email_address = data['from'][0]
            if '<' in email_address and '>' in email_address:
                email_address = email_address.split('<')[1].split('>')[0]
            if email_address.endswith(settings.EMAIL_HOST_SENDER):
                users = ESPUser.objects.filter(username__iexact=email_address.split('@')[0]).order_by('date_joined') # sort oldest to newest
            else:
                users = ESPUser.objects.filter(email__iexact=email_address).order_by('date_joined') # sort oldest to newest
            if len(users) == 0:
                logger.warning('Received email from {}, which is not associated with a user'.format(data['from']))
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
            if isinstance(data['to'], str):
                data['to'] = [data['to']]
            for recipient in data['to']:
                logger.debug(f"Sending to `{recipient}`")
                send_mail(subject=data['subject'], message=data['body'],
                         from_email='{}@{}'.format(sender, settings.EMAIL_HOST_SENDER),
                          recipient_list=[recipient], attachments=data['attachments'], fail_silently=False)
            del sender, recipient, users
        sys.exit(0)


except Exception as e:
    # we don't want to care if it's an exit
    if isinstance(e, SystemExit):
        raise

    if DEBUG:
        raise
    else:
        logger.warning("Couldn't find user '{}'. Full error is `{}`".format(user, e))
        import traceback
        error_info = traceback.format_exc()
        logger.debug("Traceback is\n{}".format(error_info))

        print("""
%s MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email %s.

""" % (ORGANIZATION_NAME, user, SUPPORT))
        sys.exit(1)
