from unittest import mock
import unittest
import sys
import fcntl

sys.modules['esp.dbmail.cronmail'] = mock.MagicMock()

with mock.patch('django.setup'):
    import dbmail_cron


class TestDbmailCron(unittest.TestCase):

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.process_messages')
    @mock.patch('dbmail_cron.send_email_requests')
    def test_happy_path(self, mock_send, mock_process, mock_lockf, mock_open):
        dbmail_cron.main()
        mock_process.assert_called_once()
        mock_send.assert_called_once()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf', side_effect=[IOError, None])
    @mock.patch('sys.exit', side_effect=SystemExit(0))
    @mock.patch('dbmail_cron.process_messages')
    def test_lock_contention(self, mock_process, mock_exit, mock_lockf, mock_open):
        with self.assertRaises(SystemExit):
            dbmail_cron.main()
        mock_exit.assert_called_once_with(0)
        mock_process.assert_not_called()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.send_email_requests')
    @mock.patch('dbmail_cron.process_messages', side_effect=Exception('DB error'))
    def test_process_messages_exception_releases_lock(self, mock_process, mock_send, mock_lockf, mock_open):
        dbmail_cron.main()
        mock_send.assert_not_called()
        unlock_call = mock_lockf.call_args_list[-1]
        assert unlock_call[0][1] == fcntl.LOCK_UN

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('dbmail_cron.fcntl.lockf')
    @mock.patch('dbmail_cron.send_email_requests', side_effect=Exception('Email error'))
    @mock.patch('dbmail_cron.process_messages')
    def test_send_email_requests_exception_releases_lock(self, mock_process, mock_send, mock_lockf, mock_open):
        dbmail_cron.main()
        mock_process.assert_called_once()
        unlock_call = mock_lockf.call_args_list[-1]
        assert unlock_call[0][1] == fcntl.LOCK_UN


if __name__ == '__main__':
    unittest.main()