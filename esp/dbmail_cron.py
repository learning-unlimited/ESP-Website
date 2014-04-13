#!/usr/bin/python

import sys
import os
import fcntl
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Forces the evaluation of the Django settings. This otherwise won't happen
# until later, because of lazy evaluation.
from django.conf import settings
dir(settings)

# This import must be after the evaluation of the Django settings, because
# esp.settings modifies tempfile to avoid collisions between sites.
import tempfile

import os.path
project = os.path.dirname(os.path.realpath(__file__))

# Path for ESP code
sys.path.insert(0, project)

# activate virtualenv
root = os.path.dirname(project)
activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
try:
    execfile(activate_this, dict(__file__=activate_this))
except IOError, e:
    # Check if a virtualenv has been installed and activated from elsewhere.
    # If this has happened, then the VIRTUAL_ENV environment variable should be
    # defined, and we can ignore the IOError.
    # If the variable isn't defined, then we really should be using our own
    # virtualenv, so we re-raise the error.
    if os.environ.get('VIRTUAL_ENV') is None:
        raise e

# lock to ensure only one cron instance runs at a time
lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.dbmailcron.lock')
lock_file_handle = open(lock_file_path, 'w')
try:
    fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance has the lock
    sys.exit(0)

from esp import cache_loader
from esp.dbmail.cronmail import process_messages, send_email_requests

process_messages()
send_email_requests()
