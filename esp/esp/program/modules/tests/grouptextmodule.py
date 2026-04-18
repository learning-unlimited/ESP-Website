__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.grouptextmodule import GroupTextModule
from django.test import override_settings
from unittest.mock import MagicMock, patch
from twilio.base.exceptions import TwilioRestException

class GroupTextModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.add_user_profiles()

    def test_is_configured_true(self):
        """Test is_configured returns true when all settings are present and typed correctly."""
        with override_settings(TWILIO_ACCOUNT_SID='AC123',
                               TWILIO_AUTH_TOKEN='token456',
                               TWILIO_ACCOUNT_NUMBERS=['+12223334444']):
            self.assertTrue(GroupTextModule.is_configured())

    def test_is_configured_false_missing_sid(self):
        """Test is_configured returns false when a required setting is missing."""
        with override_settings(TWILIO_ACCOUNT_SID=None):
            self.assertFalse(GroupTextModule.is_configured())

    def test_is_configured_false_wrong_type(self):
        """Test is_configured returns false when a setting has the wrong type."""
        with override_settings(TWILIO_ACCOUNT_NUMBERS='+12223334444'):  # Should be list/tuple
            self.assertFalse(GroupTextModule.is_configured())

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    @patch('esp.program.modules.handlers.grouptextmodule.format_number')
    def test_send_messages_success(self, mock_format, mock_client_class):
        """Test the full successful text message sending flow."""
        mock_client = mock_client_class.return_value
        mock_format.return_value = '+15555555555'

        with override_settings(TWILIO_ACCOUNT_SID='AC123',
                               TWILIO_AUTH_TOKEN='token456',
                               TWILIO_ACCOUNT_NUMBERS=['+12223334444']):
            mock_filter = MagicMock()
            student = self.students[0]
            mock_filter.getList.return_value = [student]

            with patch('esp.users.models.ContactInfo.objects.filter') as mock_ci_filter:
                mock_ci = MagicMock()
                mock_ci.phone_cell = '555-555-5555'
                mock_ci.receive_txt_message = True
                mock_ci_filter.return_value.distinct.return_value = [mock_ci]

                log = GroupTextModule.sendMessages(mock_filter, "Hello World")
                
                self.assertIn("Sending text message to +15555555555", log)
                mock_client.messages.create.assert_called_once_with(
                    body="Hello World",
                    to="+15555555555",
                    from_="+12223334444"
                )

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    @patch('esp.program.modules.handlers.grouptextmodule.format_number')
    def test_send_messages_twilio_error(self, mock_format, mock_client_class):
        """Test that mocking a TwilioRestException is handled correctly in the log."""
        mock_client = mock_client_class.return_value
        mock_client.messages.create.side_effect = TwilioRestException(400, "http://uri", "Twilio Error Message")
        mock_format.return_value = '+15555555555'

        with override_settings(TWILIO_ACCOUNT_SID='AC123',
                               TWILIO_AUTH_TOKEN='token456',
                               TWILIO_ACCOUNT_NUMBERS=['+12223334444']):
            mock_filter = MagicMock()
            student = self.students[0]
            mock_filter.getList.return_value = [student]

            with patch('esp.users.models.ContactInfo.objects.filter') as mock_ci_filter:
                mock_ci = MagicMock()
                mock_ci.phone_cell = '555-555-5555'
                mock_ci.receive_txt_message = True
                mock_ci_filter.return_value.distinct.return_value = [mock_ci]

                log = GroupTextModule.sendMessages(mock_filter, "Hello")
                self.assertIn("Twilio Error Message", log)

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    @patch('esp.program.modules.handlers.grouptextmodule.format_number')
    def test_send_messages_opt_out(self, mock_format, mock_client_class):
        """Test that users who opted out of text messages are skipped unless override is True."""
        mock_client = mock_client_class.return_value
        mock_format.return_value = '+15555555555'

        with override_settings(TWILIO_ACCOUNT_SID='AC123',
                               TWILIO_AUTH_TOKEN='token456',
                               TWILIO_ACCOUNT_NUMBERS=['+12223334444']):
            mock_filter = MagicMock()
            student = self.students[0]
            mock_filter.getList.return_value = [student]

            with patch('esp.users.models.ContactInfo.objects.filter') as mock_ci_filter:
                mock_ci = MagicMock()
                mock_ci.phone_cell = '555-555-5555'
                mock_ci.receive_txt_message = False  # Student opted out
                mock_ci_filter.return_value.distinct.return_value = [mock_ci]

                # Without override
                log = GroupTextModule.sendMessages(mock_filter, "Hello", override=False)
                self.assertIn("does not want text messages, fine", log)
                mock_client.messages.create.assert_not_called()

                # With override
                log = GroupTextModule.sendMessages(mock_filter, "Hello", override=True)
                self.assertIn("Sending text message to +15555555555", log)
                self.assertEqual(mock_client.messages.create.call_count, 1)
