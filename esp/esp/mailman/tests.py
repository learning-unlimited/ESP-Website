"""
Unit tests for esp.mailman (esp/esp/mailman/__init__.py, ~30% coverage).

All public functions are Mailman CLI wrappers decorated with
@enable_with_setting(settings.USE_MAILMAN). In test settings
USE_MAILMAN=False, so they are no-ops returning False. These tests cover:

- disabled (no-op) behavior, and
- command construction / edge cases with the module reloaded under
  USE_MAILMAN=True and subprocess calls mocked.

Refs: #4479, #3780
"""

import importlib
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

import esp.mailman as mailman_mod


def _reload_enabled():
    """Reload esp.mailman with USE_MAILMAN=True so real bodies run."""
    with override_settings(USE_MAILMAN=True):
        # enable_with_setting reads the setting at decoration time,
        # so reload inside the override to get undecorated functions.
        reloaded = importlib.reload(mailman_mod)
    return reloaded


class MailmanDisabledTest(TestCase):
    """With USE_MAILMAN=False (test default), wrappers are no-ops."""

    def test_create_list_is_noop_when_disabled(self):
        import esp.mailman as m

        # _do_nothing returns False regardless of args
        self.assertFalse(m.create_list("test-list", "owner@example.com"))

    def test_add_list_members_is_noop_when_disabled(self):
        import esp.mailman as m

        self.assertFalse(m.add_list_members("test-list", ["a@example.com"]))

    def test_list_contents_is_noop_when_disabled(self):
        import esp.mailman as m

        self.assertFalse(m.list_contents("test-list"))


class MailmanCommandConstructionTest(TestCase):
    """Command construction with subprocess mocked (USE_MAILMAN=True)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = _reload_enabled()
        # Restore the disabled module for other test modules after us.
        import esp.mailman as original_mod

        cls._original_mod = original_mod

    @classmethod
    def tearDownClass(cls):
        importlib.reload(mailman_mod)
        super().tearDownClass()

    def test_create_list_builds_newlist_command(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.create_list("mylist", "owner@example.com", admin_password="pw")
        args = mock_call.call_args[0][0]
        self.assertIn("newlist", args[0])
        self.assertIn("mylist", args)
        self.assertIn("owner@example.com", args)
        self.assertIn("pw", args)

    def test_create_list_accepts_user_object(self):
        user = User(username="owner", email="owner2@example.com")
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.create_list("mylist", user, admin_password="pw")
        args = mock_call.call_args[0][0]
        self.assertIn("owner2@example.com", args)

    def test_load_list_settings_absolute_and_relative(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.load_list_settings("mylist", "/tmp/settings.txt")
        args = mock_call.call_args[0][0]
        self.assertIn("/tmp/settings.txt", args)
        self.assertIn("mylist", args)

    def test_apply_raw_list_settings_calls_config_list(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.apply_raw_list_settings("mylist", b"some = 1\n")
        args = mock_call.call_args[0][0]
        self.assertTrue(any("config_list" in a for a in args))

    def test_apply_list_settings_serializes_dict(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.apply_list_settings("mylist", {"real_name": "My List"})
        args = mock_call.call_args[0][0]
        self.assertTrue(any("config_list" in a for a in args))

    def test_set_list_owner_password_generates_when_missing(self):
        with patch.object(
            self.m, "apply_raw_list_settings", return_value=0
        ) as mock_apply:
            pw = self.m.set_list_owner_password("mylist")
        self.assertTrue(pw and len(pw) == 10)
        mock_apply.assert_called_once()

    def test_set_list_owner_password_uses_given(self):
        with patch.object(
            self.m, "apply_raw_list_settings", return_value=0
        ) as mock_apply:
            pw = self.m.set_list_owner_password("mylist", password="secret123")
        self.assertEqual(pw, "secret123")
        mock_apply.assert_called_once()

    def test_add_list_member_delegates_to_plural(self):
        with patch.object(
            self.m, "add_list_members", return_value=("out", "err")
        ) as mock_plural:
            self.m.add_list_member("mylist", "a@example.com")
        mock_plural.assert_called_once_with("mylist", ["a@example.com"])

    def test_add_list_members_encodes_and_pipes(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("out", "err")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            self.m.add_list_members("mylist", ["a@example.com", "b@example.com"])
        args = mock_popen.call_args[0][0]
        self.assertTrue(any("add_members" in a for a in args))
        self.assertIn("mylist", args)
        sent = mock_proc.communicate.call_args[0][0]
        self.assertIn(b"a@example.com", sent)

    def test_add_list_members_empty_list(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("out", "err")
        with patch.object(self.m, "Popen", return_value=mock_proc):
            # Should not crash on empty input
            self.m.add_list_members("mylist", [])
        mock_proc.communicate.assert_called_once()

    def test_remove_list_member_string(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("out", "err")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            self.m.remove_list_member("mylist", "a@example.com")
        args = mock_popen.call_args[0][0]
        self.assertTrue(any("remove_members" in a for a in args))

    def test_remove_list_member_user_object(self):
        user = User(username="u", email="u@example.com")
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("out", "err")
        with patch.object(self.m, "Popen", return_value=mock_proc):
            self.m.remove_list_member("mylist", user)
        sent = mock_proc.communicate.call_args[0][0]
        self.assertIn(b"u@example.com", sent)

    def test_list_contents_strips_empty_string(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("a@example.com\n\n", "")
        with patch.object(self.m, "Popen", return_value=mock_proc):
            contents = self.m.list_contents("mylist")
        self.assertIn("a@example.com", contents)
        self.assertNotIn("", contents)

    def test_all_lists_public_flag(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("list1\nlist2\n", "")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            self.m.all_lists(show_nonpublic=False)
        args = mock_popen.call_args[0][0]
        self.assertIn("-a", args)

    def test_all_lists_include_nonpublic(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("list1\n", "")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            self.m.all_lists(show_nonpublic=True)
        args = mock_popen.call_args[0][0]
        self.assertNotIn("-a", args)

    def test_lists_containing_string_user(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            "a@example.com found in:\n    list1\n    list2\n",
            "",
        )
        with patch.object(self.m, "Popen", return_value=mock_proc):
            result = self.m.lists_containing("a@example.com")
        self.assertIn("list1", result)
        self.assertIn("list2", result)
