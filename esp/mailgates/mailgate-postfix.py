#!/esp/env/bin/python

# Main mailgate for ESP.
# Handles incoming messages etc.

import sys, os, email, re, smtplib, socket, hashlib, random, email.utils
new_path = '/'.join(sys.path[0].split('/')[:-1])
sys.path += [new_path]
sys.path.insert(0, "/usr/sbin/")
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

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
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

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
BOUNCES = settings.DEFAULT_EMAIL_ADDRESSES['bounces']

DEBUG=False

user = "UNKNOWN USER"

def send_mail(message, envelope_from):
    p = os.popen("%s -i -t -f %s" % (MAIL_PATH, envelope_from), 'w')
    p.write(str(message))

try:
    #user = os.environ['LOCAL_PART']
    user = sys.argv[2]

    message = email.message_from_file(sys.stdin)

    # reject e-mails that have subjects indicating they are bounce messages
    if 'subject' in message and ('Undelivered Mail Returned' in message['subject']
                                 or 'Returned mail' in message['subject']
                                 or 'Delayed Mail (still being retried)' in message['subject']):
        sys.exit(0)

    handlers = EmailList.objects.all()

    for handler in handlers:
        re_obj = re.compile(handler.regex)
        match = re_obj.search(user)


        if not match: continue

        Class = getattr(__import__(import_location + handler.handler.lower(), (), (), ['']), handler.handler)

        instance = Class(handler, message)

        instance.process(user, *match.groups(), **match.groupdict())

        envelope_from = BOUNCES  # send bounces to this address

        if handler.handler in ["ClassList", "SectionList"]:
            # The Mailman handlers: the first email to a list triggers list
            # creation by these handlers; subsequent emails are processed on
            # esp-mail without being bounced to esp-web.

            # We need to rewrite Delivered-To before bouncing the email back to
            # esp-mail, otherwise it will be eaten by bounce processing
            del message['delivered-to']

            # Also, preserve the original return-path
            _, envelope_from = email.utils.parseaddr(message['return-path'])

        if not instance.send:
            continue

        if hasattr(instance, "direct_send") and instance.direct_send:
            if message['Bcc']:
                bcc_recipients = [x.strip() for x in message['Bcc'].split(',')]
                bcc_recipients += [ARCHIVE]
                del(message['Bcc'])
                message['Bcc'] = ", ".join(bcc_recipients)
            else:
                message['Bcc'] = ARCHIVE

            send_mail(message, envelope_from)
            continue

        del(message['to'])
        del(message['cc'])
        message['Bcc'] = ARCHIVE

        if handler.subject_prefix:
            subject = message['subject']
            del(message['subject'])
            message['Subject'] = '%s%s' % (handler.subject_prefix,
                                           subject)

        if handler.from_email:
            del(message['from'])
            message['From'] = handler.from_email

        del message['Message-ID']

        # get a new message id
        message['Message-ID'] = '<%s@%s>' % (hashlib.sha1(str(random.random()).encode()).hexdigest(),
                                             host)

        if handler.cc_all:
            # send one mass-email
            message['To'] = ', '.join(instance.recipients)
            send_mail(message, envelope_from)
        else:
            # send an email for each recipient
            for recipient in instance.recipients:
                del(message['To'])
                message['To'] = recipient
                send_mail(message, envelope_from)

        sys.exit(0)


except Exception as e:
    # we dont' want to care if it's an exit
    if isinstance(e, SystemExit):
        raise

    if DEBUG:
        raise
    else:
        print("""
ESP MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email %s.

-Educational Studies Program


""" % (user, SUPPORT))
        sys.exit(1)
