#!/usr/bin/env python
"""Cron script: process queued ESP dbmail messages and send email requests.

Acquires an exclusive lock so only one instance runs at a time.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Bootstrap: add the project root to sys.path so esp_setup can be found, then
# let it configure the virtualenv and Django.  This replaces the old manual
# path-munging / virtualenv-activation / django.setup() block.
# ---------------------------------------------------------------------------
_project = os.path.dirname(os.path.realpath(__file__))
if _project not in sys.path:
    sys.path.insert(0, _project)

import esp_setup  # noqa: F401 — imported for side-effects

# ---------------------------------------------------------------------------
# Regular script imports (must come after Django is configured).
# ---------------------------------------------------------------------------
import fcntl
import logging

# This import must be after Django settings are evaluated because
# esp.settings modifies tempfile to avoid collisions between sites.
import tempfile

from esp.dbmail.cronmail import process_messages, send_email_requests

logger = logging.getLogger('esp.dbmail_cron')

logger.info('dbmail_cron: starting!')

# Lock to ensure only one cron instance runs at a time.
lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.dbmailcron.lock')
lock_file_handle = open(lock_file_path, 'w')
try:
    fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # Another instance has the lock.
    logger.info('dbmail_cron: exiting because another instance has the lock.')
    sys.exit(0)

try:
    logger.info('dbmail_cron: beginning to process messages.')
    process_messages()
    logger.info('dbmail_cron: message processing complete; sending emails.')
    send_email_requests()
    logger.info('dbmail_cron: sent emails.')
except Exception as e:
    logger.info('dbmail_cron: fatal error!')
    logger.exception(e)
finally:
    # Release the lock when message sending is complete.
    fcntl.lockf(lock_file_handle, fcntl.LOCK_UN)
    lock_file_handle.close()

logger.info('dbmail_cron: done.')
