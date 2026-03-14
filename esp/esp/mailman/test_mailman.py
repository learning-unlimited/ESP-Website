"""
Unit tests for esp/esp/mailman/__init__.py
"""
from unittest.mock import MagicMock, patch

from django.test import override_settings

from esp.tests.util import ProgramFrameworkTest


def _popen(stdout=b"", stderr=b""):
    """Return a mock Popen whose .communicate() returns (stdout, stderr)."""
    proc = MagicMock()
    proc.communicate.return_value = (stdout, stderr)
    return proc


_MAILMAN_ON = dict(
    USE_MAILMAN=True,
    MAILMAN_PATH="/usr/lib/mailman/bin/",
    MAILMAN_PASSWORD="test-admin-password",
)

_MAILMAN_OFF = dict(
    USE_MAILMAN=False,
    MAILMAN_PATH="/usr/sbin/",
    MAILMAN_PASSWORD="",
)

@override_settings(**_MAILMAN_ON)
class CreateListTest(ProgramFrameworkTest):

    @patch("esp.mailman.call", return_value=0)
    def test_email_string_owner(self, mock_call):
        from esp.mailman import create_list
        result = create_list("mylist", "owner@example.com")
        self.assertEqual(result, 0)
        mock_call.assert_called_once_with([
            "/usr/lib/mailman/bin/newlist", "-q",
            "mylist", "owner@example.com", "test-admin-password",
        ])

    @patch("esp.mailman.call", return_value=0)
    def test_user_object_owner_extracts_email(self, mock_call):
        from esp.mailman import create_list
        create_list("mylist", self.admin_user)
        args = mock_call.call_args[0][0]
        self.assertIn(self.admin_user.email, args)

    @patch("esp.mailman.call", return_value=0)
    def test_custom_admin_password(self, mock_call):
        from esp.mailman import create_list
        create_list("mylist", "owner@example.com", admin_password="custom")
        args = mock_call.call_args[0][0]
        self.assertIn("custom", args)

    @patch("esp.mailman.call", return_value=1)
    def test_error_return_code_propagated(self, mock_call):
        from esp.mailman import create_list
        result = create_list("badlist", "owner@example.com")
        self.assertEqual(result, 1)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import create_list
        self.assertIsNone(create_list("mylist", "owner@example.com"))

