#!/usr/bin/python

import sys
sys.path += ['/esp/web/esp/']
sys.path += ['/esp/web/esp/esp/']
sys.path += ['/esp/web/esp/django/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp import cache_loader
import esp.manage
from esp.dbmail.cronmail import send_miniblog_messages, process_messages, send_email_requests
#send_event_notices_for_day('tomorrow')
#send_miniblog_messages()
msgs = process_messages()
send_email_requests(msgs)
