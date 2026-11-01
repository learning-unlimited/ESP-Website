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
from esp.users.models import ESPUser


def _reload_enabled():
    """Reload esp.mailman with USE_MAILMAN=True so real bodies run."""
    with override_settings(
        USE_MAILMAN=True,
        MAILMAN_PASSWORD="test-password",
        MAILMAN_PATH="/usr/lib/mailman/bin/",
    ):
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

    def _config_list_call(self, func, *args):
        """Run func with call() mocked; return (command, settings file contents).

        The settings file is a NamedTemporaryFile that is deleted once func
        returns, so read it while call() is running.
        """
        written = {}

        def fake_call(cmd):
            with open(cmd[2], "rb") as f:
                written["data"] = f.read()
            return 0

        with patch.object(self.m, "call", side_effect=fake_call) as mock_call:
            func(*args)
        return mock_call.call_args[0][0], written["data"]

    def test_load_list_settings_absolute_path(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.load_list_settings("mylist", "/tmp/settings.txt")
        self.assertEqual(
            mock_call.call_args[0][0],
            ["/usr/lib/mailman/bin/config_list", "-i", "/tmp/settings.txt", "mylist"],
        )

    @override_settings(PROJECT_ROOT="/srv/esp/project")
    def test_load_list_settings_relative_path_uses_project_root(self):
        with patch.object(self.m, "call", return_value=0) as mock_call:
            self.m.load_list_settings("mylist", "mailman/settings.txt")
        self.assertEqual(
            mock_call.call_args[0][0],
            [
                "/usr/lib/mailman/bin/config_list",
                "-i",
                "/srv/esp/project/mailman/settings.txt",
                "mylist",
            ],
        )

    def test_apply_raw_list_settings_writes_bytes_data(self):
        cmd, data = self._config_list_call(
            self.m.apply_raw_list_settings, "mylist", b"some = 1\n"
        )
        self.assertEqual(cmd[:2], ["/usr/lib/mailman/bin/config_list", "-i"])
        self.assertEqual(cmd[3], "mylist")
        self.assertEqual(data, b"some = 1\n")

    def test_apply_raw_list_settings_encodes_str_data(self):
        _, data = self._config_list_call(
            self.m.apply_raw_list_settings, "mylist", "some = 1\n"
        )
        self.assertEqual(data, b"some = 1\n")

    def test_apply_list_settings_serializes_dict(self):
        cmd, data = self._config_list_call(
            self.m.apply_list_settings,
            "mylist",
            {"real_name": "My List", "max_message_size": 0},
        )
        self.assertEqual(cmd[:2], ["/usr/lib/mailman/bin/config_list", "-i"])
        self.assertEqual(cmd[3], "mylist")
        self.assertEqual(
            data.decode().splitlines(),
            ["real_name = 'My List'", "max_message_size = 0"],
        )

    def test_set_list_owner_password_generates_when_missing(self):
        with patch.object(
            self.m, "apply_raw_list_settings", return_value=0
        ) as mock_apply:
            pw = self.m.set_list_owner_password("mylist")
        self.assertEqual(len(pw), 10)
        mock_apply.assert_called_once()
        list_name, data = mock_apply.call_args[0]
        self.assertEqual(list_name, "mylist")
        self.assertIn("mlist.password = sha.new('%s').hexdigest()" % pw, data)

    def test_set_list_owner_password_uses_given(self):
        with patch.object(
            self.m, "apply_raw_list_settings", return_value=0
        ) as mock_apply:
            pw = self.m.set_list_owner_password("mylist", password="secret123")
        self.assertEqual(pw, "secret123")
        mock_apply.assert_called_once()
        self.assertIn(
            "mlist.password = sha.new('secret123').hexdigest()",
            mock_apply.call_args[0][1],
        )

    def test_set_list_moderator_password_sets_mod_password(self):
        with patch.object(
            self.m, "apply_raw_list_settings", return_value=0
        ) as mock_apply:
            pw = self.m.set_list_moderator_password("mylist", password="modpw")
        self.assertEqual(pw, "modpw")
        self.assertIn(
            "mlist.mod_password = sha.new('modpw').hexdigest()",
            mock_apply.call_args[0][1],
        )

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

    # Popen is not opened in text mode, so communicate() returns bytes; the
    # mocks below return bytes to match.

    def test_list_contents_strips_empty_string(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"a@example.com\nb@example.com\n", b"")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            contents = self.m.list_contents("mylist")
        self.assertEqual(
            mock_popen.call_args[0][0], ["/usr/lib/mailman/bin/list_members", "mylist"]
        )
        self.assertEqual(contents, ["a@example.com", "b@example.com"])

    def test_list_contents_decodes_non_ascii(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Jos\u00e9 <j@example.com>\n".encode("iso-8859-1"), b"")
        with patch.object(self.m, "Popen", return_value=mock_proc):
            contents = self.m.list_contents("mylist")
        self.assertEqual(contents, ["Jos\u00e9 <j@example.com>"])

    def test_all_lists_public_flag(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"list1\nlist2\n", b"")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            result = self.m.all_lists(show_nonpublic=False)
        self.assertEqual(
            mock_popen.call_args[0][0], ["/usr/lib/mailman/bin/list_lists", "-b", "-a"]
        )
        self.assertEqual(result, ["list1", "list2"])

    def test_all_lists_include_nonpublic(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"list1\n", b"")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            result = self.m.all_lists(show_nonpublic=True)
        self.assertEqual(
            mock_popen.call_args[0][0], ["/usr/lib/mailman/bin/list_lists", "-b"]
        )
        self.assertEqual(result, ["list1"])

    def test_all_lists_empty_output(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        with patch.object(self.m, "Popen", return_value=mock_proc):
            self.assertEqual(self.m.all_lists(), [])

    def test_lists_containing_string_user(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            b"a@example.com found in:\n    list1\n    list2\n",
            b"",
        )
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            result = self.m.lists_containing("a@example.com")
        self.assertEqual(
            mock_popen.call_args[0][0],
            ["/usr/lib/mailman/bin/find_member", "^a@example.com$"],
        )
        self.assertEqual(result, ["list1", "list2"])

    def test_lists_containing_skips_member_headers(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            b"a@example.com found in:\n    list1\nA@example.com found in:\n    list2\n",
            b"",
        )
        with patch.object(self.m, "Popen", return_value=mock_proc):
            result = self.m.lists_containing("a@example.com")
        self.assertEqual(result, ["list1", "list2"])

    def test_lists_containing_user_object_matches_email_or_username(self):
        user = User(username="alice", email="alice@example.com")
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"alice@example.com found in:\n    list1\n", b"")
        with patch.object(self.m, "Popen", return_value=mock_proc) as mock_popen:
            self.m.lists_containing(user)
        self.assertEqual(
            mock_popen.call_args[0][0][1],
            "^(alice@example.com|alice@esp.mit.edu)$",
        )

    def test_list_members_matches_email_and_esp_mit_edu_username(self):
        by_email = ESPUser.objects.create(username="alice", email="alice@example.com")
        by_username = ESPUser.objects.create(username="bob", email="bob@example.com")
        ESPUser.objects.create(username="carol", email="carol@example.com")
        with patch.object(
            self.m,
            "list_contents",
            return_value=["alice@example.com", "bob@esp.mit.edu", "nobody@example.com"],
        ) as mock_contents:
            members = self.m.list_members("mylist")
        mock_contents.assert_called_once_with("mylist")
        self.assertEqual(set(members), {by_email, by_username})

    def test_list_members_empty_list(self):
        ESPUser.objects.create(username="alice", email="alice@example.com")
        with patch.object(self.m, "list_contents", return_value=[]):
            self.assertFalse(self.m.list_members("mylist").exists())
