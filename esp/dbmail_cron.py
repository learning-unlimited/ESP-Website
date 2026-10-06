#!/usr/bin/env python
"""
Cron entry-point for outgoing ESP mail.
Fixes #4481: Resource leaks and incorrect log level for fatal errors.
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)

def setup_environment():
    """Original bootstrap logic - preserved exactly, moved into function for testability."""
    # Absolute path to this file's directory
    esp = os.path.dirname(os.path.abspath(__file__))
    # Absolute path to the project root (one level up from esp/)
    project = os.path.dirname(esp)

    # Check if a virtualenv has been installed in a directory called "env"
    # in the project root. If so, activate it.
    if os.environ.get('VIRTUAL_ENV') is None:
        activate_this = os.path.join(project, 'env', 'bin', 'activate_this.py')
        if os.path.exists(activate_this):
            with open(activate_this, "rb") as f:
                code = compile(f.read(), activate_this, 'exec')
            exec(code, dict(__file__=activate_this))

    # Add project to sys.path if not present
    if project not in sys.path:
        sys.path.insert(0, project)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

def main():
    # Setup env BEFORE importing Django stuff
    setup_environment()

    import django
    from django import db

    try:
        django.setup()
    except Exception:
        logger.exception("dbmail_cron: Fatal error - Django setup failed")
        return 1

    # Import after setup to avoid side effects on import
    from esp.dbmail.cronmail import process_messages, send_email_requests

    lock_file = None
    lock_path = "/tmp/dbmail_cron.lock"

    try:
        # Acquire lock file - FIX: handle will be closed in finally
        lock_file = open(lock_path, "w")

        try:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.error("dbmail_cron: Another instance is already running. Exiting.")
            return 1
        except ImportError:
            # fcntl not available on Windows - skip locking for dev
            logger.warning("dbmail_cron: fcntl not available, skipping file lock")

        logger.info("dbmail_cron: Starting process_messages()")
        process_messages()

        logger.info("dbmail_cron: Starting send_email_requests()")
        send_email_requests()

        logger.info("dbmail_cron: Completed successfully")
        return 0

    except Exception:
        # FIX #4481: Was logged at wrong level before. Now ERROR + traceback
        logger.exception("dbmail_cron: Fatal error during cron run")
        return 1

    finally:
        # FIX #4481: Resource leak fix - ALWAYS executed, even on crash
        if lock_file is not None:
            try:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                lock_file.close()
                logger.debug("dbmail_cron: Lock file released and closed")

        # Close DB connections to prevent connection leak in cron
        try:
            db.connections.close_all()
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(main())
    