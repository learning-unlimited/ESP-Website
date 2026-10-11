#!/usr/bin/env python
"""Cron entry-point for outgoing ESP mail."""

from __future__ import absolute_import

import io
import logging
import os
import sys

logger = logging.getLogger(__name__)


def setup_environment():
    """Configure the project environment before importing Django."""
    esp = os.path.dirname(os.path.abspath(__file__))
    project = os.path.dirname(esp)

    if os.environ.get("VIRTUAL_ENV") is None:
        activate_this = os.path.join(
            project, "env", "bin", "activate_this.py"
        )
        if os.path.exists(activate_this):
            with io.open(activate_this, "rb") as activation_file:
                code = compile(
                    activation_file.read(), activate_this, "exec"
                )
            exec(code, {"__file__": activate_this})

    if project not in sys.path:
        sys.path.insert(0, project)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")


def main():
    """Run the outgoing mail cron job."""
    lock_file = None
    lock_acquired = False
    fcntl = None
    db = None

    try:
        setup_environment()

        import django
        from django import db as django_db

        db = django_db
        django.setup()

        # Import after Django initialization.
        from esp.dbmail.cronmail import (
            process_messages,
            send_email_requests,
        )

        # ESP settings may customize tempfile, so import it afterward.
        import tempfile
        import fcntl as fcntl_module

        fcntl = fcntl_module

        lock_path = os.path.join(
            tempfile.gettempdir(),
            "espweb.dbmailcron.lock",
        )
        lock_file = io.open(lock_path, "w")

        try:
            fcntl.lockf(
                lock_file,
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
            lock_acquired = True
        except BlockingIOError:
            logger.info(
                "dbmail_cron: exiting because another instance "
                "has the lock."
            )
            return 0

        logger.info("dbmail_cron: beginning to process messages.")
        process_messages()

        logger.info(
            "dbmail_cron: message processing complete; sending emails."
        )
        send_email_requests()

        logger.info("dbmail_cron: sent emails.")
        logger.info("dbmail_cron: done.")
        return 0

    except Exception:
        logger.exception("dbmail_cron: fatal error!")
        return 1

    finally:
        if lock_file is not None:
            try:
                if lock_acquired and fcntl is not None:
                    fcntl.lockf(lock_file, fcntl.LOCK_UN)
            except Exception:
                logger.exception(
                    "dbmail_cron: failed to release lock"
                )
            finally:
                try:
                    lock_file.close()
                except Exception:
                    logger.exception(
                        "dbmail_cron: failed to close lock file"
                    )

        if db is not None:
            try:
                db.connections.close_all()
            except Exception:
                logger.exception(
                    "dbmail_cron: failed to close database connections"
                )


if __name__ == "__main__":
    sys.exit(main())
