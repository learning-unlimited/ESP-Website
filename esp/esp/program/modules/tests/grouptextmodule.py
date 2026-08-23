__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

from unittest.mock import patch

from django.db.models import Q
from django.test import override_settings

from esp.program.models import RegistrationProfile
from esp.program.modules.handlers.grouptextmodule import GroupTextModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ContactInfo, ESPUser, PersistentQueryFilter

TWILIO_SETTINGS = {
    'TWILIO_ACCOUNT_SID': 'test_sid',
    'TWILIO_AUTH_TOKEN': 'test_token',
    'TWILIO_ACCOUNT_NUMBERS': ['+15005550006'],
}


def _make_filter(users):
    q = Q(id__in=[u.id for u in users])
    filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
    return filterObj


class GroupTextModuleSendMessagesTest(ProgramFrameworkTest):
    """Regression tests for GroupTextModule.sendMessages."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 3, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.add_user_profiles()

    def _make_contact_info(self, user, phone='+12015551234', receive_txt=True):
        ci = ContactInfo.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            e_mail=user.email,
            phone_cell=phone,
            receive_txt_message=receive_txt,
        )
        rp = RegistrationProfile(user=user, program=self.program, contact_user=ci, most_recent_profile=True)
        rp.save()
        return ci

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_user_without_contact_info_is_skipped(self, mock_client_cls):
        """User with no ContactInfo linked via RegistrationProfile.contact_user must be skipped, not crash."""
        user_no_ci = self.students[0]
        # Ensure no ContactInfo linked as direct contact for this user.
        ContactInfo.objects.filter(user=user_no_ci, as_user__isnull=False).delete()

        filterObj = _make_filter([user_no_ci])
        log = GroupTextModule.sendMessages(filterObj, 'hello')

        self.assertIn('Could not find contact info for', log)
        mock_client_cls.return_value.messages.create.assert_not_called()

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_user_opted_out_is_skipped(self, mock_client_cls):
        """User with receive_txt_message=False must be skipped without override."""
        user = self.students[1]
        self._make_contact_info(user, receive_txt=False)

        filterObj = _make_filter([user])
        log = GroupTextModule.sendMessages(filterObj, 'hello')

        self.assertIn('does not want text messages', log)
        mock_client_cls.return_value.messages.create.assert_not_called()

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_user_opted_out_but_override_sends(self, mock_client_cls):
        """User with receive_txt_message=False receives text when override=True."""
        user = self.students[1]
        self._make_contact_info(user, receive_txt=False)

        filterObj = _make_filter([user])
        GroupTextModule.sendMessages(filterObj, 'hello', override=True)

        mock_client_cls.return_value.messages.create.assert_called_once()

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_message_sent_to_user_with_contact_info(self, mock_client_cls):
        """User with valid ContactInfo and receive_txt_message=True receives the message."""
        user = self.students[2]
        self._make_contact_info(user, receive_txt=True)

        filterObj = _make_filter([user])
        log = GroupTextModule.sendMessages(filterObj, 'test message')

        mock_client_cls.return_value.messages.create.assert_called_once()
        call_kwargs = mock_client_cls.return_value.messages.create.call_args[1]
        self.assertEqual(call_kwargs['body'], 'test message')
        self.assertIn('Found contact info for', log)

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_mixed_users_partial_send(self, mock_client_cls):
        """Users with and without contact info are processed correctly; only eligible users receive texts."""
        user_no_ci = self.students[0]
        ContactInfo.objects.filter(user=user_no_ci, as_user__isnull=False).delete()

        user_with_ci = self.students[2]
        self._make_contact_info(user_with_ci, receive_txt=True)

        filterObj = _make_filter([user_no_ci, user_with_ci])
        log = GroupTextModule.sendMessages(filterObj, 'hello')

        self.assertIn('Could not find contact info for', log)
        self.assertIn('Found contact info for', log)
        mock_client_cls.return_value.messages.create.assert_called_once()


class GroupTextModuleConfiguredTest(ProgramFrameworkTest):
    """Tests for GroupTextModule.is_configured and panel access."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 1, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)

    def test_is_configured_true_with_settings(self):
        with override_settings(**TWILIO_SETTINGS):
            self.assertTrue(GroupTextModule.is_configured())

    def test_is_configured_false_without_sid(self):
        with override_settings(
            TWILIO_ACCOUNT_SID=None,
            TWILIO_AUTH_TOKEN='tok',
            TWILIO_ACCOUNT_NUMBERS=['+15005550006'],
        ):
            self.assertFalse(GroupTextModule.is_configured())

    def test_is_configured_false_without_numbers(self):
        with override_settings(
            TWILIO_ACCOUNT_SID='sid',
            TWILIO_AUTH_TOKEN='tok',
            TWILIO_ACCOUNT_NUMBERS=None,
        ):
            self.assertFalse(GroupTextModule.is_configured())

    @override_settings(**TWILIO_SETTINGS)
    def test_panel_renders_when_configured(self):
        self.assertTrue(
            self.client.login(username=self.admins[0].username, password='password')
        )
        response = self.client.get('/manage/%s/grouptextpanel' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/grouptextmodule/search.html')

    def test_panel_not_configured_template(self):
        with override_settings(TWILIO_ACCOUNT_SID=None):
            self.assertTrue(
                self.client.login(username=self.admins[0].username, password='password')
            )
            response = self.client.get('/manage/%s/grouptextpanel' % self.program.url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(
                response, 'program/modules/grouptextmodule/not_configured.html'
            )

    def test_student_cannot_access_panel(self):
        with override_settings(**TWILIO_SETTINGS):
            self.assertTrue(
                self.client.login(username=self.students[0].username, password='password')
            )
            response = self.client.get('/manage/%s/grouptextpanel' % self.program.url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    @override_settings(**TWILIO_SETTINGS)
    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_send_messages_handles_twilio_error(self, mock_client_cls):
        from twilio.base.exceptions import TwilioRestException

        user = self.students[0]
        self.add_user_profiles()
        ContactInfo.objects.filter(user=user).delete()
        ci = ContactInfo.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            e_mail=user.email,
            phone_cell='+12015551234',
            receive_txt_message=True,
        )
        RegistrationProfile(
            user=user, program=self.program, contact_user=ci, most_recent_profile=True
        ).save()

        mock_client_cls.return_value.messages.create.side_effect = TwilioRestException(
            status=400, uri='/Messages', msg='Twilio boom'
        )
        filter_obj = _make_filter([user])
        log = GroupTextModule.sendMessages(filter_obj, 'hello')
        self.assertIn('Twilio boom', log)
