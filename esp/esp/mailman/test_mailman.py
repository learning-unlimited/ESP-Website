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

@override_settings(**_MAILMAN_ON)
class LoadListSettingsTest(ProgramFrameworkTest):

    @patch("esp.mailman.call", return_value=0)
    def test_absolute_path_used_unchanged(self, mock_call):
        from esp.mailman import load_list_settings
        load_list_settings("mylist", "/abs/path/settings.cfg")
        args = mock_call.call_args[0][0]
        self.assertIn("/abs/path/settings.cfg", args)

    @patch("esp.mailman.call", return_value=0)
    def test_relative_path_joined_to_project_root(self, mock_call):
        from esp.mailman import load_list_settings
        with self.settings(PROJECT_ROOT="/srv/esp"):
            load_list_settings("mylist", "configs/list.cfg")
        args = mock_call.call_args[0][0]
        self.assertIn("/srv/esp/configs/list.cfg", args)

    @patch("esp.mailman.call", return_value=0)
    def test_list_name_in_command(self, mock_call):
        from esp.mailman import load_list_settings
        load_list_settings("targetlist", "/some/file.cfg")
        args = mock_call.call_args[0][0]
        self.assertIn("targetlist", args)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import load_list_settings
        self.assertIsNone(load_list_settings("mylist", "/some/file.cfg"))

@override_settings(**_MAILMAN_ON)
class ApplyRawListSettingsTest(ProgramFrameworkTest):

    @patch("esp.mailman.call", return_value=0)
    def test_bytes_data_calls_config_list(self, mock_call):
        from esp.mailman import apply_raw_list_settings
        result = apply_raw_list_settings("mylist", b"key = 'value'\n")
        self.assertEqual(result, 0)
        cmd = mock_call.call_args[0][0]
        self.assertIn("config_list", cmd[0])
        self.assertIn("-i", cmd)
        self.assertIn("mylist", cmd)

    @patch("esp.mailman.call", return_value=0)
    def test_string_data_accepted(self, mock_call):
        from esp.mailman import apply_raw_list_settings
        result = apply_raw_list_settings("mylist", "key = 'value'\n")
        self.assertEqual(result, 0)

    @patch("esp.mailman.call", return_value=0)
    def test_correct_content_written_to_tempfile(self, mock_call):
        import tempfile
        from esp.mailman import apply_raw_list_settings

        written = []
        original_ntf = tempfile.NamedTemporaryFile

        class CapturingNTF:
            def __init__(self, **kwargs):
                self._f = original_ntf(**kwargs)
                self.name = self._f.name
            def write(self, data):
                written.append(data)
                return self._f.write(data)
            def flush(self):
                return self._f.flush()
            def __enter__(self):
                self._f.__enter__()
                return self
            def __exit__(self, *args):
                return self._f.__exit__(*args)

        with patch("esp.mailman.NamedTemporaryFile", CapturingNTF):
            apply_raw_list_settings("mylist", b"expected-content")

        self.assertIn(b"expected-content", written)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import apply_raw_list_settings
        self.assertIsNone(apply_raw_list_settings("mylist", b"data"))

@override_settings(**_MAILMAN_ON)
class ApplyListSettingsTest(ProgramFrameworkTest):

    @patch("esp.mailman.call", return_value=0)
    def test_dict_keys_and_values_serialised(self, mock_call):
        import tempfile
        from esp.mailman import apply_list_settings

        written = []
        original_ntf = tempfile.NamedTemporaryFile

        class CapturingNTF:
            def __init__(self, **kwargs):
                self._f = original_ntf(**kwargs)
                self.name = self._f.name
            def write(self, data):
                written.append(data)
                return self._f.write(data)
            def flush(self):
                return self._f.flush()
            def __enter__(self):
                self._f.__enter__()
                return self
            def __exit__(self, *args):
                return self._f.__exit__(*args)

        with patch("esp.mailman.NamedTemporaryFile", CapturingNTF):
            apply_list_settings("mylist", {"archive": True, "max_message_size": 40})

        combined = b"".join(written).decode("utf-8")
        self.assertIn("archive", combined)
        self.assertIn("max_message_size", combined)

    @patch("esp.mailman.call", return_value=0)
    def test_returns_call_result(self, mock_call):
        from esp.mailman import apply_list_settings
        self.assertEqual(apply_list_settings("mylist", {"x": "y"}), 0)

    @patch("esp.mailman.call", return_value=0)
    def test_empty_dict_does_not_raise(self, mock_call):
        from esp.mailman import apply_list_settings
        self.assertEqual(apply_list_settings("mylist", {}), 0)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import apply_list_settings
        self.assertIsNone(apply_list_settings("mylist", {"k": "v"}))

@override_settings(**_MAILMAN_ON)
class SetListOwnerPasswordTest(ProgramFrameworkTest):

    @patch("esp.mailman.apply_raw_list_settings")
    def test_provided_password_returned(self, mock_apply):
        from esp.mailman import set_list_owner_password
        result = set_list_owner_password("mylist", password="secret123")
        self.assertEqual(result, "secret123")

    @patch("esp.mailman.apply_raw_list_settings")
    def test_password_is_sha256_hashed(self, mock_apply):
        import hashlib
        from esp.mailman import set_list_owner_password
        set_list_owner_password("mylist", password="secret123")
        written = mock_apply.call_args[0][1]
        expected = hashlib.sha256("secret123".encode()).hexdigest()
        self.assertIn(expected, written)

    @patch("esp.mailman.apply_raw_list_settings")
    def test_no_deprecated_sha_module_in_config(self, mock_apply):
        from esp.mailman import set_list_owner_password
        set_list_owner_password("mylist", password="pw")
        written = mock_apply.call_args[0][1]
        self.assertNotIn("import sha", written)

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.apply_raw_list_settings")
    def test_random_password_generated_when_none_given(self, mock_apply, mock_esp):
        from esp.mailman import set_list_owner_password
        mock_esp.objects.make_random_password.return_value = "rand-pw"
        result = set_list_owner_password("mylist")
        self.assertEqual(result, "rand-pw")

    @patch("esp.mailman.apply_raw_list_settings")
    def test_correct_list_name_forwarded(self, mock_apply):
        from esp.mailman import set_list_owner_password
        set_list_owner_password("specificlist", password="pw")
        self.assertEqual(mock_apply.call_args[0][0], "specificlist")

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import set_list_owner_password
        self.assertIsNone(set_list_owner_password("mylist", password="pw"))

@override_settings(**_MAILMAN_ON)
class SetListModeratorPasswordTest(ProgramFrameworkTest):

    @patch("esp.mailman.apply_raw_list_settings")
    def test_provided_password_returned(self, mock_apply):
        from esp.mailman import set_list_moderator_password
        result = set_list_moderator_password("mylist", password="modpass")
        self.assertEqual(result, "modpass")

    @patch("esp.mailman.apply_raw_list_settings")
    def test_mod_password_attribute_used(self, mock_apply):
        from esp.mailman import set_list_moderator_password
        set_list_moderator_password("mylist", password="modpass")
        written = mock_apply.call_args[0][1]
        self.assertIn("mod_password", written)

    @patch("esp.mailman.apply_raw_list_settings")
    def test_password_is_sha256_hashed(self, mock_apply):
        import hashlib
        from esp.mailman import set_list_moderator_password
        set_list_moderator_password("mylist", password="modpass")
        written = mock_apply.call_args[0][1]
        expected = hashlib.sha256("modpass".encode()).hexdigest()
        self.assertIn(expected, written)

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.apply_raw_list_settings")
    def test_random_password_generated_when_none(self, mock_apply, mock_esp):
        from esp.mailman import set_list_moderator_password
        mock_esp.objects.make_random_password.return_value = "rand-mod"
        result = set_list_moderator_password("mylist")
        self.assertEqual(result, "rand-mod")

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import set_list_moderator_password
        self.assertIsNone(set_list_moderator_password("mylist", password="pw"))

@override_settings(**_MAILMAN_ON)
class AddListMemberTest(ProgramFrameworkTest):

    @patch("esp.mailman.add_list_members")
    def test_delegates_to_add_list_members_with_list(self, mock_alm):
        from esp.mailman import add_list_member
        mock_alm.return_value = (b"", b"")
        add_list_member("mylist", "user@example.com")
        mock_alm.assert_called_once_with("mylist", ["user@example.com"])

    @patch("esp.mailman.add_list_members")
    def test_user_object_wrapped_in_list(self, mock_alm):
        from esp.mailman import add_list_member
        mock_alm.return_value = (b"", b"")
        add_list_member("mylist", self.student)
        mock_alm.assert_called_once_with("mylist", [self.student])

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import add_list_member
        self.assertIsNone(add_list_member("mylist", "user@example.com"))

@override_settings(**_MAILMAN_ON)
class AddListMembersTest(ProgramFrameworkTest):

    @patch("esp.mailman.Popen")
    def test_email_strings_piped_to_stdin(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import add_list_members
        add_list_members("mylist", ["a@example.com", "b@example.com"])
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(b"a@example.com", communicated)
        self.assertIn(b"b@example.com", communicated)

    @patch("esp.mailman.Popen")
    def test_list_name_in_command(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import add_list_members
        add_list_members("targetlist", ["x@example.com"])
        cmd = mock_popen.call_args[0][0]
        self.assertIn("targetlist", cmd)

    @patch("esp.mailman.Popen")
    def test_empty_members_produces_empty_bytes(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import add_list_members
        add_list_members("mylist", [])
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertEqual(communicated, b"")

    @patch("esp.mailman.Popen")
    def test_output_is_iso8859_encoded_bytes(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import add_list_members
        add_list_members("mylist", ["user@example.com"])
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIsInstance(communicated, bytes)

    @patch("esp.mailman.Popen")
    def test_multiple_members_separated_by_newline(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import add_list_members
        add_list_members("mylist", ["a@x.com", "b@x.com"])
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(b"\n", communicated)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import add_list_members
        self.assertIsNone(add_list_members("mylist", ["user@example.com"]))

@override_settings(**_MAILMAN_ON)
class RemoveListMemberTest(ProgramFrameworkTest):

    @patch("esp.mailman.Popen")
    def test_email_string_piped_to_stdin(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import remove_list_member
        remove_list_member("mylist", "gone@example.com")
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(b"gone@example.com", communicated)

    @patch("esp.mailman.Popen")
    def test_user_object_email_extracted(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import remove_list_member
        remove_list_member("mylist", self.student)
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(self.student.email.encode("iso-8859-1", "replace"), communicated)

    @patch("esp.mailman.Popen")
    def test_list_of_emails_joined_and_encoded(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import remove_list_member
        remove_list_member("mylist", ["a@example.com", "b@example.com"])
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(b"a@example.com", communicated)
        self.assertIn(b"b@example.com", communicated)
        self.assertIn(b"\n", communicated)

    @patch("esp.mailman.Popen")
    def test_queryset_like_object_with_filter_attr(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import remove_list_member
        u1, u2 = MagicMock(), MagicMock()
        u1.email = "qs1@example.com"
        u2.email = "qs2@example.com"
        mock_qs = MagicMock()
        mock_qs.filter = MagicMock()
        mock_qs.__iter__ = MagicMock(return_value=iter([u1, u2]))
        remove_list_member("mylist", mock_qs)
        communicated = mock_popen.return_value.communicate.call_args[0][0]
        self.assertIn(b"qs1@example.com", communicated)
        self.assertIn(b"qs2@example.com", communicated)

    @patch("esp.mailman.Popen")
    def test_nouserack_noadminack_flags_in_command(self, mock_popen):
        mock_popen.return_value = _popen()
        from esp.mailman import remove_list_member
        remove_list_member("mylist", "x@example.com")
        cmd = mock_popen.call_args[0][0]
        self.assertIn("--nouserack", cmd)
        self.assertIn("--noadminack", cmd)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import remove_list_member
        self.assertIsNone(remove_list_member("mylist", "user@example.com"))

@override_settings(**_MAILMAN_ON)
class ListContentsTest(ProgramFrameworkTest):

    @patch("esp.mailman.Popen")
    def test_returns_email_list_from_stdout(self, mock_popen):
        mock_popen.return_value = _popen(stdout=b"a@example.com\nb@example.com\n")
        from esp.mailman import list_contents
        result = list_contents("mylist")
        self.assertIn("a@example.com", result)
        self.assertIn("b@example.com", result)

    @patch("esp.mailman.Popen")
    def test_empty_strings_stripped(self, mock_popen):
        mock_popen.return_value = _popen(stdout=b"a@example.com\n\n")
        from esp.mailman import list_contents
        result = list_contents("mylist")
        self.assertNotIn("", result)

    @patch("esp.mailman.Popen")
    def test_bytes_decoded_to_strings(self, mock_popen):
        mock_popen.return_value = _popen(stdout=b"user@test.com\n")
        from esp.mailman import list_contents
        result = list_contents("mylist")
        self.assertTrue(all(isinstance(r, str) for r in result))

    @patch("esp.mailman.Popen")
    def test_empty_output_returns_empty_list(self, mock_popen):
        mock_popen.return_value = _popen(stdout=b"")
        from esp.mailman import list_contents
        result = list_contents("mylist")
        self.assertEqual(result, [])

    @patch("esp.mailman.Popen")
    def test_list_name_passed_in_command(self, mock_popen):
        mock_popen.return_value = _popen(stdout=b"")
        from esp.mailman import list_contents
        list_contents("specificlist")
        cmd = mock_popen.call_args[0][0]
        self.assertIn("specificlist", cmd)

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import list_contents
        self.assertIsNone(list_contents("mylist"))

@override_settings(**_MAILMAN_ON)
class ListMembersTest(ProgramFrameworkTest):

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.list_contents")
    def test_filters_by_email_and_esp_username(self, mock_lc, mock_esp):
        from esp.mailman import list_members
        mock_lc.return_value = ["user@example.com", "jsmith@esp.mit.edu"]
        mock_esp.objects.filter.return_value = MagicMock()
        list_members("mylist")
        mock_esp.objects.filter.assert_called_once()

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.list_contents")
    def test_username_extracted_from_esp_mit_edu_addresses(self, mock_lc, mock_esp):
        from esp.mailman import list_members
        mock_lc.return_value = ["jsmith@esp.mit.edu"]
        mock_esp.objects.filter.return_value = MagicMock()
        list_members("mylist")
        mock_esp.objects.filter.assert_called_once()

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.list_contents")
    def test_non_esp_domain_not_split_as_username(self, mock_lc, mock_esp):
        from esp.mailman import list_members
        mock_lc.return_value = ["user@gmail.com"]
        mock_esp.objects.filter.return_value = MagicMock()
        list_members("mylist")
        mock_esp.objects.filter.assert_called_once()

    @patch("esp.mailman.ESPUser")
    @patch("esp.mailman.list_contents")
    def test_empty_list_still_calls_filter(self, mock_lc, mock_esp):
        from esp.mailman import list_members
        mock_lc.return_value = []
        mock_esp.objects.filter.return_value = MagicMock()
        list_members("mylist")
        mock_esp.objects.filter.assert_called_once()

    @override_settings(**_MAILMAN_OFF)
    def test_disabled_returns_none(self):
        from esp.mailman import list_members
        self.assertIsNone(list_members("mylist"))
