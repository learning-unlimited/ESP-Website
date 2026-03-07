from unittest import mock
import sys
import fcntl
import unittest

sys.modules['django'] = mock.MagicMock()
sys.modules['esp.dbmail.cronmail'] = mock.MagicMock()

import dbmail_cron

class TestDbmailCron(unittest.TestCase):

    @mock.patch('dbmail_cron.send_email_requests')
    @mock.patch('dbmail_cron.process_messages')
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('sys.exit')
    @mock.patch('dbmail_cron.process_messages')
    @mock.patch('dbmail_cron.fcntl.lockf', side_effect=IOError)
    @mock.patch('builtins.open', mock.mock_open())
    def test_lock_contention(self, mock_lockf, mock_process, mock_exit):
        dbmail_cron.main()

        mock_exit.assert_called_once_with(0)
        mock_process.assert_not_called()
    def test_happy_path(self, mock_lockf, mock_process, mock_send):
        dbmail_cron.main()

        mock_process.assert_called_once()
        mock_send.assert_called_once()