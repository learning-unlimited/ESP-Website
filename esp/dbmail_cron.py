from __future__ import absolute_import

import os
import runpy
import fcntl

from unittest.mock import MagicMock, call, patch

from esp.dbmail import cronmail
from esp.tests.util import CacheFlushTestCase


class DbmailCronTest(CacheFlushTestCase):

    def _run_script(self, lock_side_effect=None,
                    process_side_effect=None):
        lock_handle = MagicMock()

        with patch.dict(
            os.environ,
            {'VIRTUAL_ENV': '/test/virtualenv'},
            clear=False
        ), patch('django.setup'), \
                patch('io.open', return_value=lock_handle), \
                patch('tempfile.gettempdir', return_value='/tmp'), \
                patch('logging.getLogger') as get_logger, \
                patch('fcntl.lockf') as lockf, \
                patch.object(
                    cronmail,
                    'process_messages'
                ) as process_messages, \
                patch.object(
                    cronmail,
                    'send_email_requests'
                ) as send_email_requests:

            if lock_side_effect is not None:
                lockf.side_effect = lock_side_effect

            if process_side_effect is not None:
                process_messages.side_effect = process_side_effect

            logger = get_logger.return_value

            state = {
                'lock_handle': lock_handle,
                'lockf': lockf,
                'process_messages': process_messages,
                'send_email_requests': send_email_requests,
                'logger': logger,
                'system_exit': None,
            }

            try:
                runpy.run_path(
                    '/app/esp/dbmail_cron.py',
                    run_name='__main__'
                )
            except SystemExit as exc:
                state['system_exit'] = exc

        return state

    def test_successful_processing(self):
        state = self._run_script()

        state['process_messages'].assert_called_once_with()
        state['send_email_requests'].assert_called_once_with()

        state['lockf'].assert_has_calls([
            call(
                state['lock_handle'],
                fcntl.LOCK_EX | fcntl.LOCK_NB
            ),
            call(
                state['lock_handle'],
                fcntl.LOCK_UN
            ),
        ])

        state['lock_handle'].close.assert_called_once_with()
        self.assertIsNone(state['system_exit'])

    def test_exits_when_lock_is_already_taken(self):
        state = self._run_script(
            lock_side_effect=IOError()
        )

        self.assertIsNotNone(state['system_exit'])
        self.assertEqual(state['system_exit'].code, 0)

        state['process_messages'].assert_not_called()
        state['send_email_requests'].assert_not_called()

        state['lock_handle'].close.assert_called_once_with()

        state['lockf'].assert_called_once_with(
            state['lock_handle'],
            fcntl.LOCK_EX | fcntl.LOCK_NB
        )

        state['logger'].info.assert_any_call(
            'dbmail_cron: exiting because another instance has the lock.'
        )

    def test_handles_processing_error(self):
        error = RuntimeError('test processing error')

        state = self._run_script(
            process_side_effect=error
        )

        state['process_messages'].assert_called_once_with()
        state['send_email_requests'].assert_not_called()

        state['logger'].info.assert_any_call(
            'dbmail_cron: fatal error!'
        )

        state['logger'].exception.assert_called_once_with(error)

        state['lockf'].assert_has_calls([
            call(
                state['lock_handle'],
                fcntl.LOCK_EX | fcntl.LOCK_NB
            ),
            call(
                state['lock_handle'],
                fcntl.LOCK_UN
            ),
        ])

        state['lock_handle'].close.assert_called_once_with()
        self.assertIsNone(state['system_exit'])
import logging
from io import open
logger = logging.getLogger('esp.dbmail_cron')   # __name__ is not very useful
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
    with open(activate_this, "rb") as f:
        exec(compile(f.read(), activate_this, 'exec'), dict(__file__=activate_this))

import django
django.setup()
from esp.dbmail.cronmail import process_messages, send_email_requests

# This import must be after the evaluation of the Django settings, because
# esp.settings modifies tempfile to avoid collisions between sites.
import tempfile

logger.info('dbmail_cron: starting!')

# lock to ensure only one cron instance runs at a time
lock_file_path = os.path.join(tempfile.gettempdir(), 'espweb.dbmailcron.lock')
lock_file_handle = open(lock_file_path, 'w')
try:
    fcntl.lockf(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance has the lock
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
    # Release the lock when message sending is complete.
    fcntl.lockf(lock_file_handle, fcntl.LOCK_UN)
    lock_file_handle.close()

logger.info('dbmail_cron: done.')
