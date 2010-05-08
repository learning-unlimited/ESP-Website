#!/usr/bin/python

# Main mailgate for ESP.
# Handles incoming messages etc.

import sys, os, operator, email, re, smtplib, socket, sha, random
new_path = '/'.join(sys.path[0].split('/')[:-1])
sys.path += [new_path]
sys.path.insert(0, "/lu/sites/stanford/esp")
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp import cache_loader # Needed to block an annoying circular-dependency issue
from esp.dbmail.models import EmailList

host = socket.gethostname()
import_location = 'esp.dbmail.receivers.'
MAIL_PATH = '/usr/sbin/sendmail'
server = smtplib.SMTP('localhost')
ARCHIVE = 'learninguarchive@gmail.com'

DEBUG=True
DEBUG=False

if DEBUG:
    sys.stdout = open('/tmp/stdout', 'w',)
    sys.stderr = open('/tmp/stderr', 'w',)

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

        
        del(message['to'])
        del(message['cc'])
        message['X-ESP-SENDER'] = 'version 2'
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


except Exception,e:
    a = sys.exc_info()

    # we dont' want to care if it's an exit
    if isinstance(e,SystemExit):
        raise a[0],a[1],a[2]
        

    if DEBUG:
        raise a[0],a[1],a[2]
    else:
        print """
ESP MAIL SERVER
===============

Could not find user "%s"

If you are experiencing difficulty, please email stanford-websupport@lists.learningu.org.

-Educational Studies Program


""" % user
        sys.exit(1)
