from unittest import mock
import importlib.util
import pathlib

from django.test import SimpleTestCase

def load_cron_module():
    path = pathlib.Path(__file__).resolve().parents[2] / "dbmail_cron.py"
    spec = importlib.util.spec_from_file_location("dbmail_cron", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class DbmailCronTest(SimpleTestCase):

    def test_import_does_not_run_cron(self):
        """Importing the module should NOT run the cron job."""
        with mock.patch("esp.dbmail.cronmail.process_messages") as pm:
            load_cron_module()
            pm.assert_not_called()

    @mock.patch("esp.dbmail.cronmail.send_email_requests")
    @mock.patch("esp.dbmail.cronmail.process_messages")
    def test_main_success(self, mock_process, mock_send):
        """main() should call both functions and return 0."""
        cron = load_cron_module()
        with mock.patch.object(cron, "setup_django"), \
             mock.patch("builtins.open", mock.mock_open()), \
             mock.patch("fcntl.flock"):
            result = cron.main()
        self.assertEqual(result, 0)
        mock_process.assert_called_once()
        mock_send.assert_called_once()

    @mock.patch("esp.dbmail.cronmail.process_messages", side_effect=RuntimeError("DB down"))
    def test_main_logs_error_and_closes_lock(self, mock_process):
        """On failure, should log ERROR and close lock file (leak fix)."""
        cron = load_cron_module()
        mock_file_obj = mock.mock_open()()

        with mock.patch.object(cron, "setup_django"), \
             mock.patch("builtins.open", return_value=mock_file_obj), \
             mock.patch("fcntl.flock"), \
             self.assertLogs(cron.logger, level="ERROR"):
            result = cron.main()

        self.assertEqual(result, 1)
        mock_file_obj.close.assert_called()