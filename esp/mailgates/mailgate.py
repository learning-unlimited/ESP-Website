#!/usr/bin/env python

# Main mailgate
# Handles incoming messages etc.

import sys
import os

# ---------------------------------------------------------------------------
# Bootstrap: locate the project root (the esp/ directory that sits one level
# above this file's mailgates/ directory), add it to sys.path, then delegate
# all virtualenv activation, DJANGO_SETTINGS_MODULE configuration, and
# django.setup() to the shared esp_setup module.
# ---------------------------------------------------------------------------
_project = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _project not in sys.path:
    sys.path.insert(0, _project)

import esp_setup  # noqa: F401 — imported for side-effects

import logging
# Make sure we end up in our logger even though this file is outside esp/esp/
logger = logging.getLogger('esp.mailgate')

import email
import re
import smtplib
import socket
import hashlib
import random

from esp.dbmail.models import EmailList
from django.conf import settings

import email.utils
from django.core.mail import send_mail as django_send_mail
from esp.users.models import ESPUser

host = socket.gethostname()
import_location = 'esp.dbmail.receivers.'
MAIL_PATH = '/usr/sbin/sendmail'
server = smtplib.SMTP('localhost')
ARCHIVE = settings.DEFAULT_EMAIL_ADDRESSES['archive']
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']
ORGANIZATION_NAME = settings.INSTITUTION_NAME + '_' + settings.ORGANIZATION_SHORT_NAME

#DEBUG=True
DEBUG=False

user = "UNKNOWN USER"

def send_mail(message):
    p = os.popen("%s -i -t" % MAIL_PATH, 'w')
    p.write(message)

try:
    user = os.environ['LOCAL_PART']

    message = email.message_from_bytes(sys.stdin.buffer.read())

    handlers = EmailList.objects.all()

    matched_any_handler = False

    for handler in handlers:
        re_obj = re.compile(handler.regex)
        match = re_obj.search(user)

        if not match: continue

        matched_any_handler = True

        Class = getattr(__import__(import_location + handler.handler.lower(), (), (), ['']), handler.handler)

        instance = Class(handler, message)

        instance.process(user, *match.groups(), **match.groupdict())

        if not instance.send:
            continue

        if not getattr(instance, 'preserve_headers', False):
            # Group broadcasts (ClassList, SectionList, PlainList):
            # Strip headers, prefix subject, regen Message-ID
            del(message['to'])
            del(message['cc'])
            message['X-ESP-SENDER'] = 'version 2'
            message['X-FORWARDED-FOR'] = message['X-CLIENT-IP'] if message['X-Client-IP'] else message['Client-IP']

            subject = message['subject']
            del(message['subject'])
            if hasattr(instance, 'emailcode') and instance.emailcode:
                subject = '[%s] %s' % (instance.emailcode, subject)
            if handler.subject_prefix:
                subject = '[%s] %s' % (handler.subject_prefix, subject)
            message['Subject'] = subject

            if handler.from_email:
                del(message['from'])
                message['From'] = handler.from_email

            del message['Message-ID']
            message['Message-ID'] = '<%s@%s>' % (hashlib.sha1(str(random.random()).encode()).hexdigest(),
                                                 host)

        # Common path for ALL handlers — iterate recipients
        if handler.cc_all:
            # send one mass-email
            del(message['To'])
            message['To'] = ', '.join(instance.recipients)
            send_mail(str(message))
        else:
            # send an email for each recipient
            for recipient in instance.recipients:
                del(message['To'])
                message['To'] = recipient
                send_mail(str(message))

        sys.exit(0)

    # ----- No handler accepted the email -----
    # Only bounce if no handler regex matched (true invalid address).
    # If a handler matched but chose not to send (permission issue), stay silent.
    if not matched_any_handler:
        _sender_name, sender_email = email.utils.parseaddr(message.get('From', ''))
        # Anti-loop: never bounce to our own system address
        if (sender_email
                and sender_email.lower() != SUPPORT.lower()
                and ESPUser.objects.filter(email__iexact=sender_email).exists()):
            try:
                django_send_mail(
                    'Undeliverable mail to %s@%s' % (user, host),
                    'Your message to "%s@%s" could not be delivered.\n\n'
                    'The address does not exist or is not currently accepting '
                    'messages. If you believe this is an error, please contact '
                    '%s for assistance.\n' % (user, host, SUPPORT),
                    SUPPORT,
                    [sender_email],
                    fail_silently=True,
                )
            except Exception:
                logger.warning("Failed to send bounce to '%s'", sender_email)

    # Exit 0 so MTA considers delivery "handled" — no native NDR bounce
    sys.exit(0)

except Exception as e:
    # we don't want to care if it's an exit
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
