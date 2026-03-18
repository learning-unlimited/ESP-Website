from __future__ import absolute_import

import unittest
import importlib
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import TestCase
import esp.mailman  # Initial import

class MailmanInteropTest(TestCase):
    """
    Tests the subprocess wrapping logic for Mailman 2.1 integration.
    Uses reload to bypass import-time decorator binding.
    """

    @classmethod
    def setUpClass(cls):
        # 1. Patch settings to enable the module
        cls.settings_patcher = patch.multiple(
            settings, 
            USE_MAILMAN=True, 
            MAILMAN_PATH='/usr/lib/mailman/bin/', 
            MAILMAN_PASSWORD='secret'
        )
        cls.settings_patcher.start()
        
        # 2. Force a reload so the @enable_with_setting decorator sees USE_MAILMAN=True
        importlib.reload(esp.mailman)

    @classmethod
    def tearDownClass(cls):
        cls.settings_patcher.stop()
        # Reset the module to its default state for other tests
        importlib.reload(esp.mailman)

    @patch('esp.mailman.call')
    def test_create_list_calls_binary(self, mock_call):
        """Test that create_list correctly calls the newlist binary."""
        mock_call.return_value = 0
        
        # Accessing functions directly from the reloaded module
        result = esp.mailman.create_list('test-list', 'owner@learningu.org', 'password')
        
        expected_cmd = ['/usr/lib/mailman/bin/newlist', '-q', 'test-list', 'owner@learningu.org', 'password']
        mock_call.assert_called_once_with(expected_cmd)
        self.assertEqual(result, 0)

    @patch('esp.mailman.Popen')
    def test_add_list_members_piping(self, mock_popen):
        """Verify emails are joined and encoded as iso-8859-1 for Mailman's stdin."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'Success', b'')
        mock_popen.return_value = mock_process
        
        members = ['student1@learningu.org', 'student2@learningu.org']
        result = esp.mailman.add_list_members('test-list', members)
        
        # Check stdin payload
        expected_payload = b'student1@learningu.org\nstudent2@learningu.org'
        mock_process.communicate.assert_called_once_with(expected_payload)
        self.assertEqual(result, (b'Success', b''))

    @patch('esp.mailman.call')
    @patch('esp.mailman.NamedTemporaryFile')
    def test_apply_list_settings_serialization(self, mock_tempfile, mock_call):
        """Verify dict is serialized to Python assignments in a temp file."""
        mock_file = MagicMock()
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_file.name = '/tmp/config.txt'
        
        settings_dict = {'archive': True}
        esp.mailman.apply_list_settings('test-list', settings_dict)
        
        # Verify serialization logic (key = repr(value))
        mock_file.writelines.assert_called_once()
        lines = list(mock_file.writelines.call_args[0][0])
        self.assertIn("archive = True\n", lines)

    @patch('esp.mailman.Popen')
    def test_list_contents_parsing(self, mock_popen):
        """Verify list_contents removes the trailing empty string from stdout."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('user1@ex.com\nuser2@ex.com\n', '') 
        mock_popen.return_value = mock_process
        
        result = esp.mailman.list_contents('test-list')
        self.assertEqual(result, ['user1@ex.com', 'user2@ex.com'])

    @patch('esp.mailman.Popen')
    def test_all_lists_flags(self, mock_popen):
        """Verify correct CLI flags (-b, -a) for public vs private lists."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('list1\n', '')
        mock_popen.return_value = mock_process
        
        # Default restricted to advertised (-a)
        esp.mailman.all_lists(show_nonpublic=False)
        self.assertIn('-a', mock_popen.call_args[0][0])
        
        # Non-public (no -a)
        mock_popen.reset_mock()
        esp.mailman.all_lists(show_nonpublic=True)
        self.assertNotIn('-a', mock_popen.call_args[0][0])

class MailmanDisabledTest(unittest.TestCase):
    """Verifies default behavior when Mailman is disabled."""
    
    def test_returns_false_when_disabled(self):
        # Force reload with False to ensure names are bound to _do_nothing
        with patch.object(settings, 'USE_MAILMAN', False):
            importlib.reload(esp.mailman)
            result = esp.mailman.create_list('any', 'any')
            self.assertFalse(result)