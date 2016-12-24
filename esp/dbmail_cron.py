#!/usr/bin/env python

import sys
import os
import fcntl
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import os.path
project = os.path.dirname(os.path.realpath(__file__))

# Path for ESP code
sys.path.insert(0, project)

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    if os.path.isfile(activate_this):
        execfile(activate_this, dict(__file__=activate_this))

import django
django.setup()
from esp.dbmail.cronmail import process_messages, send_email_requests

# This import must be after the evaluation of the Django settings, because
# esp.settings modifies tempfile to avoid collisions between sites.
import tempfile

# lock to ensure only one cron instance runs at a time
lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.dbmailcron.lock')
lock_file_handle = open(lock_file_path, 'w')
try:
    fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance has the lock
    sys.exit(0)

process_messages()
send_email_requests()

# Release the lock when message sending is complete.
fcntl.lockf(lock_file_handle, fcntl.LOCK_UN)
lock_file_handle.close()
