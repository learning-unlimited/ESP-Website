#!/usr/bin/env python

# Main mailgate for ESP.
# Handles incoming messages etc.

import sys, os, email, re, smtplib, socket, sha, random
new_path = '/'.join(sys.path[0].split('/')[:-1])
sys.path += [new_path]
sys.path.insert(0, "/usr/sbin/")
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import logging
# Make sure we end up in our logger even though this file is outside esp
logger = logging.getLogger('esp.mailgate')

import os.path
project = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Path for ESP code
sys.path.insert(0, project)

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

import django
django.setup()
from esp.dbmail.models import EmailList
from django.conf import settings

host = socket.gethostname()
import_location = 'esp.dbmail.receivers.'
MAIL_PATH = '/usr/sbin/sendmail'
server = smtplib.SMTP('localhost')
ARCHIVE = settings.DEFAULT_EMAIL_ADDRESSES['archive']
SUPPORT = settings.DEFAULT_EMAIL_ADDRESSES['support']

DEBUG=True
DEBUG=False

#os.environ['LOCAL_PART'] = 'axiak'

user = "UNKNOWN USER"

def send_mail(message):
    p = os.popen("%s -i -t" % MAIL_PATH, 'w')
    p.write(message)

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

        if hasattr(instance, "direct_send") and instance.direct_send:
            if message['Bcc']:
                bcc_recipients = [x.strip() for x in message['Bcc'].split(',')]
                del(message['Bcc'])
                message['Bcc'] = ", ".join(bcc_recipients)

            send_mail(str(message))
            continue

        del(message['to'])
        del(message['cc'])
        message['X-ESP-SENDER'] = 'version 2'

        subject = message['subject']
        del(message['subject'])
        if instance.emailcode:
            subject = '[%s] %s' % (instance.emailcode, subject)
        if handler.subject_prefix:
            subject = '[%s] %s' % (handler.subject_prefix, subject)
        message['Subject'] = subject

        if handler.from_email:
            del(message['from'])
            message['From'] = handler.from_email

        del message['Message-ID']

        # get a new message id
        message['Message-ID'] = '<%s@%s>' % (sha.new(str(random.random())).hexdigest(),
                                             host)

        if handler.cc_all:
            # send one mass-email
            message['To'] = ', '.join(instance.recipients)
            send_mail(str(message))
        else:
            # send an email for each recipient
            for recipient in instance.recipients:
                del(message['To'])
                message['To'] = recipient
                send_mail(str(message))

        sys.exit(0)


except Exception as e:
    # we dont' want to care if it's an exit
    if isinstance(e, SystemExit):
        raise

    if DEBUG:
        raise
    else:
        logger.warning("Couldn't find user '%s'", user)
        print """
ESP MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email %s.

-Educational Studies Program


""" % (user, SUPPORT)
        sys.exit(1)
