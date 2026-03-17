#!/usr/bin/env python
import fcntl
import logging
import os
import sys
import tempfile
from io import open

logger = logging.getLogger('esp.dbmail_cron')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')

project = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, project)

process_messages = None
send_email_requests = None


def setup_django():
    if os.environ.get('VIRTUAL_ENV') is None and not os.environ.get('GITHUB_ACTIONS'):
        root = os.path.dirname(project)
        activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
        if os.path.exists(activate_this):
            with open(activate_this, "rb") as f:
                exec(compile(f.read(), activate_this, 'exec'), dict(__file__=activate_this))
        else:
            logger.warning(
                'dbmail_cron: virtualenv activation script not found at %s; skipping activation.',
                activate_this,
            )

    import django

    django.setup()

    global process_messages, send_email_requests
    if process_messages is None or send_email_requests is None:
        from esp.dbmail.cronmail import process_messages as process_messages_fn
        from esp.dbmail.cronmail import send_email_requests as send_email_requests_fn

        process_messages = process_messages_fn
        send_email_requests = send_email_requests_fn


def main():
    setup_django()
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
