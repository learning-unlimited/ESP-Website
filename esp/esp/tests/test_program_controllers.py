"""
Tests for esp.program.controllers.confirmation
Source: esp/esp/program/controllers/confirmation.py

Tests ConfirmationEmailController: record creation, no-duplicate behavior,
and repeat sending logic.
"""
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import Group
from django.core import mail

from esp.cal.models import install as install_cal
from esp.program.controllers.confirmation import ConfirmationEmailController
from esp.program.models import Program
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser, Record, RecordType


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class ConfirmationEmailControllerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        install_cal()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.user = ESPUser.objects.create_user(
            username='confirmer',
            email='confirmer@example.com',
            password='password',
        )
        self.controller = ConfirmationEmailController()
        RecordType.objects.get_or_create(name='conf_email')

    @patch('esp.program.controllers.confirmation.send_mail')
    def test_send_confirmation_email_creates_record(self, mock_send_mail):
        """Sending a confirmation email should create a Record for the user."""
        mock_options = MagicMock()
        mock_options.send_confirmation = True

        with patch.object(
            type(self.program), 'studentclassregmoduleinfo',
            new_callable=lambda: property(lambda self: mock_options),
        ):
            self.controller.send_confirmation_email(self.user, self.program, override=True)

        rt = RecordType.objects.get(name='conf_email')
        self.assertTrue(Record.objects.filter(user=self.user, event=rt, program=self.program).exists())

    @patch('esp.program.controllers.confirmation.send_mail')
    def test_no_duplicate_without_repeat(self, mock_send_mail):
        """Sending twice without repeat=True should not send a second email."""
        mock_options = MagicMock()
        mock_options.send_confirmation = True

        with patch.object(
            type(self.program), 'studentclassregmoduleinfo',
            new_callable=lambda: property(lambda self: mock_options),
        ):
            self.controller.send_confirmation_email(self.user, self.program, override=True)
            call_count_1 = mock_send_mail.call_count
            self.controller.send_confirmation_email(self.user, self.program, override=True)
            call_count_2 = mock_send_mail.call_count

        self.assertEqual(call_count_1, call_count_2)

    @patch('esp.program.controllers.confirmation.send_mail')
    def test_repeat_sends_again(self, mock_send_mail):
        """With repeat=True, a second email should be sent."""
        mock_options = MagicMock()
        mock_options.send_confirmation = True

        with patch.object(
            type(self.program), 'studentclassregmoduleinfo',
            new_callable=lambda: property(lambda self: mock_options),
        ):
            self.controller.send_confirmation_email(self.user, self.program, override=True)
            self.controller.send_confirmation_email(self.user, self.program, repeat=True, override=True)

        self.assertEqual(mock_send_mail.call_count, 2)
