#!/usr/bin/env python
"""
Cron entry-point for outgoing ESP mail.
Fixes #4481: Resource leaks and incorrect log level for fatal errors.
"""
import logging
import os
import sys

import django
from django import db

logger = logging.getLogger(__name__)

LOCK_FILE_PATH = "/tmp/dbmail_cron.lock"

def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")
    django.setup()

def main():
    # Import inside function so importing this file doesn't run cron
    from esp.dbmail.cronmail import process_messages, send_email_requests

    setup_django()

    lock_file = None
    try:
        lock_file = open(LOCK_FILE_PATH, "w")

        try:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.error("dbmail_cron: Another instance is already running. Exiting.")
            return 1

        logger.info("dbmail_cron: Starting process_messages()")
        process_messages()

        logger.info("dbmail_cron: Starting send_email_requests()")
        send_email_requests()

        logger.info("dbmail_cron: Completed successfully")
        return 0

    except Exception:
        # Fixed: Fatal errors now logged at ERROR level with traceback
        logger.exception("dbmail_cron: Fatal error during cron run")
        return 1

    finally:
        # Fixed: Always close resources to prevent leaks
        if lock_file is not None:
            try:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                lock_file.close()
                logger.debug("dbmail_cron: Lock file released")

        db.connections.close_all()

if __name__ == "__main__":
    sys.exit(main())