#!/usr/bin/env python
import sys
import os
import fcntl
import logging
from io import open
logger = logging.getLogger('esp.dbmail_cron')

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import os.path
project = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, project)

if os.environ.get('VIRTUAL_ENV') is None:
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    with open(activate_this, "rb") as f:
        exec(compile(f.read(), activate_this, 'exec'), dict(__file__=activate_this))

import django
django.setup()

from esp.dbmail.cronmail import process_messages, send_email_requests
import tempfile


def main():
    logger.info('dbmail_cron: starting!')

    lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.dbmailcron.lock')
    lock_file_handle = open(lock_file_path, 'w')

    try:
        fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.info('dbmail_cron: exiting because another instance has the lock.')
        lock_file_handle.close()
        sys.exit(0)

    try:
        logger.info('dbmail_cron: beginning to process messages.')
        process_messages()
        logger.info('dbmail_cron: message processing complete; sending emails.')
        send_email_requests()
        logger.info('dbmail_cron: sent emails.')
    except Exception as e:
        logger.error('dbmail_cron: fatal error!')
        logger.exception(e)
    finally:
        fcntl.lockf(lock_file_handle, fcntl.LOCK_UN)
        lock_file_handle.close()

    logger.info('dbmail_cron: done.')


if __name__ == '__main__':
    main()