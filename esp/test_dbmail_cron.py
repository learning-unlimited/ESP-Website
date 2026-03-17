import sys
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import fcntl
except ImportError:
    fcntl = SimpleNamespace(LOCK_EX=1, LOCK_NB=2, LOCK_UN=8, lockf=mock.Mock())
    sys.modules['fcntl'] = fcntl

import dbmail_cron


class TestDbmailCron(unittest.TestCase):
    @mock.patch('dbmail_cron.setup_django')
    @mock.patch('dbmail_cron.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.process_messages')
    @mock.patch('dbmail_cron.send_email_requests')
    def test_happy_path(
        self,
        mock_send,
        mock_process,
        mock_lockf,
        mock_open,
        mock_setup_django,
    ):
        dbmail_cron.main()

        mock_setup_django.assert_called_once_with()
        mock_process.assert_called_once_with()
        mock_send.assert_called_once_with()
        self.assertEqual(mock_lockf.call_args_list[-1][0][1], fcntl.LOCK_UN)
        mock_open.return_value.close.assert_called_once_with()

    @mock.patch('dbmail_cron.setup_django')
    @mock.patch('dbmail_cron.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf', side_effect=IOError)
    @mock.patch('dbmail_cron.sys.exit', side_effect=SystemExit(0))
    @mock.patch('dbmail_cron.process_messages')
    @mock.patch('dbmail_cron.send_email_requests')
    def test_lock_contention(
        self,
        mock_send,
        mock_process,
        mock_exit,
        mock_lockf,
        mock_open,
        mock_setup_django,
    ):
        with self.assertRaises(SystemExit):
            dbmail_cron.main()

        mock_setup_django.assert_called_once_with()
        mock_exit.assert_called_once_with(0)
        mock_process.assert_not_called()
        mock_send.assert_not_called()
        mock_open.return_value.close.assert_called_once_with()
        self.assertEqual(mock_lockf.call_count, 1)

    @mock.patch('dbmail_cron.setup_django')
    @mock.patch('dbmail_cron.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.send_email_requests')
    @mock.patch('dbmail_cron.process_messages', side_effect=Exception('DB error'))
    def test_process_messages_exception_releases_lock(
        self,
        mock_process,
        mock_send,
        mock_lockf,
        mock_open,
        mock_setup_django,
    ):
        dbmail_cron.main()

        mock_setup_django.assert_called_once_with()
        mock_send.assert_not_called()
        self.assertEqual(mock_lockf.call_args_list[-1][0][1], fcntl.LOCK_UN)
        mock_open.return_value.close.assert_called_once_with()

    @mock.patch('dbmail_cron.setup_django')
    @mock.patch('dbmail_cron.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.send_email_requests', side_effect=Exception('Email error'))
    @mock.patch('dbmail_cron.process_messages')
    def test_send_email_requests_exception_releases_lock(
        self,
        mock_process,
        mock_send,
        mock_lockf,
        mock_open,
        mock_setup_django,
    ):
        dbmail_cron.main()

        mock_setup_django.assert_called_once_with()
        mock_process.assert_called_once_with()
        self.assertEqual(mock_lockf.call_args_list[-1][0][1], fcntl.LOCK_UN)
        mock_open.return_value.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
