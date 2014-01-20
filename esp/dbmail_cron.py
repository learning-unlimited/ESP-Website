#!/usr/bin/python

import sys
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import os.path
project = os.path.dirname(os.path.realpath(__file__))

# Path for ESP code
sys.path.insert(0, project)

# activate virtualenv
root = os.path.dirname(project)
activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from esp import cache_loader
from esp.dbmail.cronmail import process_messages, send_email_requests

process_messages()
send_email_requests()
