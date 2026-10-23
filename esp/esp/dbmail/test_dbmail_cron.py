import errno
import importlib.util
import os
import tempfile
import unittest
from unittest import mock


CRON_SCRIPT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "dbmail_cron.py",
    )
)

SPEC = importlib.util.spec_from_file_location(
    "esp_dbmail_cron_entrypoint",
    CRON_SCRIPT,
)
cron = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cron)


class TestDbmailCron(unittest.TestCase):
    def setUp(self):
        self.lock_handle = mock.MagicMock()
        self.lock_handle.__enter__.return_value = self.lock_handle
        self.db = mock.MagicMock()

        self.patches = [
            mock.patch.object(cron, "setup_environment"),
            mock.patch("django.setup"),
            mock.patch("django.db.connections.close_all"),
            mock.patch("fcntl.lockf"),
            mock.patch("io.open", return_value=self.lock_handle),
            mock.patch("tempfile.gettempdir", return_value="/tmp"),
        ]

        self.mocks = [patcher.start() for patcher in self.patches]
        self.addCleanup(self._stop_patches)

        self.setup_environment = self.mocks[0]
        self.django_setup = self.mocks[1]
        self.close_connections = self.mocks[2]
        self.lockf = self.mocks[3]
        self.open_file = self.mocks[4]
        self.get_tempdir = self.mocks[5]

        self.process_messages = mock.patch(
            "esp.dbmail.cronmail.process_messages"
        )
        self.send_email_requests = mock.patch(
            "esp.dbmail.cronmail.send_email_requests"
        )

    def _stop_patches(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_lock_acquired_and_mail_functions_run(self):
        with self.process_messages as process, \
                self.send_email_requests as send:
            result = cron.main()

        self.assertEqual(result, 0)
        process.assert_called_once_with()
        send.assert_called_once_with()
        self.lock_handle.close.assert_called_once_with()
        self.close_connections.assert_called_once_with()

    def test_lock_contention_exits_cleanly_and_closes_handle(self):
        self.lockf.side_effect = OSError(errno.EAGAIN, "Lock unavailable")

        with self.process_messages as process, \
                self.send_email_requests as send:
            result = cron.main()

        self.assertEqual(result, 0)
        process.assert_not_called()
        send.assert_not_called()
        self.lock_handle.close.assert_called_once_with()
        self.close_connections.assert_called_once_with()

    def test_unexpected_lock_error_returns_failure(self):
        self.lockf.side_effect = OSError(errno.EIO, "Unexpected lock error")

        result = cron.main()

        self.assertEqual(result, 1)
        self.lock_handle.close.assert_called_once_with()
        self.close_connections.assert_called_once_with()

    def test_processing_error_still_releases_lock_and_closes_handle(self):
        with self.process_messages as process:
            process.side_effect = RuntimeError("Processing failed")

            result = cron.main()

        self.assertEqual(result, 1)
        self.lockf.assert_any_call(
            self.lock_handle,
            cron.fcntl.LOCK_UN,
        )
        self.lock_handle.close.assert_called_once_with()
        self.close_connections.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
