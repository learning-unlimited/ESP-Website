#!/sw/bin/python

import sys
sys.path += ['/Library/WebServer/DjangoApps/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'tmg.settings'

import manage
from esp.dbmail.cronmail import send_event_notices_for_day
send_event_notices_for_day('tomorrow')
