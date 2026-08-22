#!/usr/bin/env python
"""Advances all non-terminal LotteryRun rows via the same
guarded-refresh mechanism the status view uses, so runs keep progressing
even with no viewer polling them (and dedups with any viewer that IS
polling -- see esp.program.controllers.lottery.refresh). Run this from cron
every ~1 minute.
"""

from __future__ import absolute_import
import sys
import os
import fcntl
import logging
from io import open
logger = logging.getLogger('esp.lottery_poll_cron')   # __name__ is not very useful
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
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

import django
django.setup()

from esp.program.models import LotteryRun
from esp.program.controllers.lottery.refresh import TERMINAL_STATUSES, refresh_run_from_service

import tempfile

logger.info('lottery_poll_cron: starting!')

# lock to ensure only one cron instance runs at a time
lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.lotterypollcron.lock')
lock_file_handle = open(lock_file_path, 'w')
try:
    fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance has the lock
    logger.info('lottery_poll_cron: exiting because another instance has the lock.')
    sys.exit(0)

try:
    runs = LotteryRun.objects.exclude(status__in=TERMINAL_STATUSES)
    logger.info('lottery_poll_cron: advancing %d non-terminal run(s).', runs.count())
    for run in runs:
        try:
            refresh_run_from_service(run)
        except Exception as e:
            # One run's solver being unreachable/misconfigured shouldn't stop
            # the others from being polled this cycle.
            logger.exception('lottery_poll_cron: failed to refresh run %s: %s', run.id, e)
    logger.info('lottery_poll_cron: done.')
except Exception as e:
    logger.info('lottery_poll_cron: fatal error!')
    logger.exception(e)
finally:
    # Release the lock when polling is complete.
    fcntl.lockf(lock_file_handle, fcntl.LOCK_UN)
    lock_file_handle.close()
