from django.test import TestCase
from unittest.mock import patch
import importlib


class DBMailCronTests(TestCase):

    @patch("esp.dbmail.cronmail.send_email_requests")
    @patch("esp.dbmail.cronmail.process_messages")
    def test_process_and_send_called(self, mock_process, mock_send):
        """
        Ensure that dbmail_cron triggers process_messages
        and send_email_requests when executed.
        """

        import esp.dbmail_cron
        importlib.reload(esp.dbmail_cron)

        mock_process.assert_called()
        mock_send.assert_called()