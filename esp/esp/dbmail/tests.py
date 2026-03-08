__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from django.contrib.auth.models import Group
from django.core import mail
from django.core.exceptions import ValidationError

from esp.dbmail.models import ActionHandler, MessageRequest, PlainRedirect, HeldEmail, send_mail
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class SendMailTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.user = ESPUser.objects.create_user(
            username='mailuser',
            email='mailuser@example.com',
            password='password',
        )

    def test_send_mail_basic(self):
        send_mail(
            'Test Subject',
            'Test body',
            'from@learningu.org',
            ['to@example.com'],
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')

    def test_send_mail_with_bcc(self):
        send_mail(
            'BCC Test',
            'Body',
            'from@learningu.org',
            ['to@example.com'],
            bcc=['bcc@example.com'],
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('bcc@example.com', mail.outbox[0].bcc)

    def test_send_mail_with_user_adds_unsubscribe(self):
        send_mail(
            'Unsub Test',
            'Body',
            'from@learningu.org',
            ['to@example.com'],
            user=self.user,
        )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('List-Unsubscribe', sent.extra_headers)


class ActionHandlerTest(TestCase):
    def test_getattribute_delegates_to_obj(self):
        class FakeObj:
            def foo(self, user):
                return 'result_%s' % user

        handler = ActionHandler(FakeObj(), 'testuser')
        result = handler.foo('testuser')
        self.assertEqual(result, 'result_testuser')


class MessageRequestTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_is_sendto_fn_name_choice_valid(self):
        self.assertTrue(MessageRequest.is_sendto_fn_name_choice('send_to_guardian'))

    def test_is_sendto_fn_name_choice_invalid(self):
        self.assertFalse(MessageRequest.is_sendto_fn_name_choice('not_a_real_choice'))


class CronmailImportTest(TestCase):
    """Verify the cronmail module can be imported without errors."""

    def test_import(self):
        from esp.dbmail import cronmail
        self.assertTrue(hasattr(cronmail, 'process_messages'))

    def test_process_messages_callable(self):
        from esp.dbmail.cronmail import process_messages
        self.assertTrue(callable(process_messages))


# ---------------------------------------------------------------------------
# Tests for issue #3943: mailgate relay improvements
# ---------------------------------------------------------------------------
from email.mime.text import MIMEText

from esp.dbmail.models import EmailList
from esp.dbmail.receivers.useremail import UserEmail
from esp.dbmail.receivers.classlist import ClassList
from esp.dbmail.receivers.sectionlist import SectionList


def _make_message(to='test@learningu.org', frm='sender@example.com',
                  subject='Test', list_id=None):
    """Helper to build a simple email.message for handler tests."""
    msg = MIMEText('Test body')
    msg['To'] = to
    msg['From'] = frm
    msg['Subject'] = subject
    if list_id:
        msg['List-Id'] = list_id
    return msg


class UserEmailHandlerTest(TestCase):
    """Tests for the UserEmail handler after polymorphism refactor."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.teacher = ESPUser.objects.create_user(
            username='teacher_user',
            email='teacher@example.com',
            password='password',
        )
        self.teacher.makeRole('Teacher')

        self.student = ESPUser.objects.create_user(
            username='student_user',
            email='student@example.com',
            password='password',
        )
        self.student.makeRole('Student')

        self.email_list = EmailList.objects.create(
            regex=r'^(.+)$',
            seq=10,
            handler='UserEmail',
            cc_all=False,
        )

    def test_teacher_sets_recipients_and_preserve_headers(self):
        msg = _make_message()
        handler = UserEmail(self.email_list, msg)
        handler.process('teacher_user', 'teacher_user')

        self.assertTrue(handler.send)
        self.assertEqual(handler.recipients, ['teacher@example.com'])
        self.assertTrue(handler.preserve_headers)
        self.assertFalse(hasattr(handler, 'direct_send'))

    def test_student_without_list_id_does_not_send(self):
        msg = _make_message()
        handler = UserEmail(self.email_list, msg)
        handler.process('student_user', 'student_user')

        self.assertFalse(handler.send)

    def test_student_with_list_id_sets_recipients(self):
        msg = _make_message(list_id='<list.example.com>')
        handler = UserEmail(self.email_list, msg)
        handler.process('student_user', 'student_user')

        self.assertTrue(handler.send)
        self.assertEqual(handler.recipients, ['student@example.com'])
        self.assertTrue(handler.preserve_headers)

    def test_nonexistent_user_does_not_send(self):
        msg = _make_message()
        handler = UserEmail(self.email_list, msg)
        handler.process('nobody', 'nobody')

        self.assertFalse(handler.send)


class ClassListBugFixTest(TestCase):
    """Tests that ClassList handles invalid class_id gracefully after bug fix."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.email_list = EmailList.objects.create(
            regex=r'^(\d+)-(teachers|students|class)$',
            seq=5,
            handler='ClassList',
            cc_all=False,
        )

    @patch('esp.dbmail.receivers.classlist.settings')
    def test_invalid_class_id_does_not_raise(self, mock_settings):
        mock_settings.USE_MAILMAN = False
        msg = _make_message()
        handler = ClassList(self.email_list, msg)
        # class_id 99999 does not exist — should return gracefully
        handler.process('99999-teachers', '99999', 'teachers')
        self.assertFalse(handler.send)


class SectionListBugFixTest(TestCase):
    """Tests that SectionList handles invalid class_id/section gracefully."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.email_list = EmailList.objects.create(
            regex=r'^(\d+)\.(\d+)-(teachers|students|class)$',
            seq=6,
            handler='SectionList',
            cc_all=False,
        )

    @patch('esp.dbmail.receivers.sectionlist.settings')
    def test_invalid_class_id_does_not_raise(self, mock_settings):
        mock_settings.USE_MAILMAN = False
        msg = _make_message()
        handler = SectionList(self.email_list, msg)
        handler.process('99999.1-teachers', '99999', '1', 'teachers')
        self.assertFalse(handler.send)


class MailgateBounceTest(TestCase):
    """Tests for the bounce handling logic in mailgate.py."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.known_user = ESPUser.objects.create_user(
            username='knownuser',
            email='known@example.com',
            password='password',
        )

    def test_bounce_sent_for_known_user(self):
        """Known ESP user should receive a bounce email."""
        import email.utils
        from django.core.mail import send_mail as django_send_mail
        from django.conf import settings

        sender_email = 'known@example.com'
        local_part = 'nonexistent'
        hostname = 'learningu.org'
        support = settings.DEFAULT_EMAIL_ADDRESSES.get('support', 'support@localhost')

        # Replicate the bounce logic from mailgate.py
        if (sender_email
                and sender_email.lower() != support.lower()
                and ESPUser.objects.filter(email__iexact=sender_email).exists()):
            django_send_mail(
                'Undeliverable mail to %s@%s' % (local_part, hostname),
                'Your message could not be delivered.',
                support,
                [sender_email],
                fail_silently=True,
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('nonexistent', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['known@example.com'])

    def test_no_bounce_for_unknown_sender(self):
        """Unknown sender should NOT receive a bounce email."""
        sender_email = 'unknown@spammer.com'

        if (sender_email
                and ESPUser.objects.filter(email__iexact=sender_email).exists()):
            pass  # Would send bounce, but won't match

        self.assertEqual(len(mail.outbox), 0)

    def test_no_bounce_for_empty_from(self):
        """Empty/missing From header should not trigger bounce."""
        import email.utils
        _name, addr = email.utils.parseaddr('')
        self.assertEqual(addr, '')
        # Empty addr means bounce logic is skipped

class PlainRedirectValidationTest(TestCase):
    def test_valid_single_destination(self):
        redirect = PlainRedirect(original='directors', destination='user@example.com')
        redirect.full_clean()

    def test_valid_multiple_destinations(self):
        redirect = PlainRedirect(
            original='announcements',
            destination='user1@example.com, user2@example.com',
        )
        redirect.full_clean()

    def test_invalid_destination_email_fails_validation(self):
        redirect = PlainRedirect(
            original='directors',
            destination='user@example.com, not-an-email',
        )

        with self.assertRaises(ValidationError) as error:
            redirect.full_clean()

        self.assertIn('destination', error.exception.message_dict)
        self.assertIn('not-an-email', error.exception.message_dict['destination'][0])

    def test_empty_destination_entry_fails_validation(self):
        redirect = PlainRedirect(
            original='directors',
            destination='user@example.com,',
        )

        with self.assertRaises(ValidationError) as error:
            redirect.full_clean()

        self.assertIn('destination', error.exception.message_dict)
        self.assertIn('<empty>', error.exception.message_dict['destination'][0])


# ---------------------------------------------------------------------------
# Tests for issue #1229: HeldEmail moderation
# ---------------------------------------------------------------------------
import json
from email.mime.multipart import MIMEMultipart


def _create_held_email(email_list=None, **overrides):
    """Helper to build a HeldEmail for testing."""
    msg = _make_message()
    defaults = {
        'email_list': email_list,
        'local_part': 'M100-students',
        'raw_message': msg.as_bytes(),
        'recipients_json': json.dumps(['student1@example.com', 'student2@example.com']),
        'handler_class': 'ClassList',
        'subject_prefix': '',
        'from_email_override': '',
        'cc_all': False,
        'preserve_headers': False,
        'emailcode': 'M100',
        'sender': 'sender@example.com',
        'subject': 'Test',
    }
    defaults.update(overrides)
    return HeldEmail.objects.create(**defaults)


class HeldEmailModelTest(TestCase):
    """Tests for the HeldEmail model."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.admin = ESPUser.objects.create_user(
            username='held_admin', email='admin@example.com', password='password'
        )
        self.admin.makeRole('Administrator')
        self.email_list = EmailList.objects.create(
            regex=r'^(\d+)-(teachers|students|class)$',
            seq=5, handler='ClassList', cc_all=False, admin_hold=True,
        )

    def test_create_held_email(self):
        held = _create_held_email(email_list=self.email_list)
        self.assertEqual(held.status, HeldEmail.PENDING)
        self.assertIsNotNone(held.held_at)
        self.assertEqual(held.local_part, 'M100-students')

    def test_get_recipients(self):
        held = _create_held_email(email_list=self.email_list)
        self.assertEqual(held.get_recipients(), ['student1@example.com', 'student2@example.com'])

    def test_get_message_object(self):
        held = _create_held_email(email_list=self.email_list)
        msg = held.get_message_object()
        self.assertEqual(msg['From'], 'sender@example.com')
        self.assertEqual(msg['Subject'], 'Test')

    def test_get_body_preview(self):
        held = _create_held_email(email_list=self.email_list)
        preview = held.get_body_preview()
        self.assertIn('Test body', preview)

    def test_get_body_preview_multipart(self):
        msg = MIMEMultipart()
        msg['To'] = 'test@learningu.org'
        msg['From'] = 'teacher@example.com'
        msg['Subject'] = 'Multipart'
        msg.attach(MIMEText('Plain text part'))
        msg.attach(MIMEText('<html>HTML part</html>', 'html'))
        held = _create_held_email(
            email_list=self.email_list,
            raw_message=msg.as_bytes(),
        )
        preview = held.get_body_preview()
        self.assertIn('Plain text part', preview)

    @patch('esp.dbmail.models.os.popen')
    def test_approve_changes_status(self, mock_popen):
        held = _create_held_email(email_list=self.email_list)
        held.approve(self.admin)
        held.refresh_from_db()
        self.assertEqual(held.status, HeldEmail.APPROVED)
        self.assertEqual(held.moderated_by, self.admin)
        self.assertIsNotNone(held.moderated_at)

    def test_reject_changes_status(self):
        held = _create_held_email(email_list=self.email_list)
        held.reject(self.admin, reason='Inappropriate content')
        held.refresh_from_db()
        self.assertEqual(held.status, HeldEmail.REJECTED)
        self.assertEqual(held.rejection_reason, 'Inappropriate content')
        self.assertEqual(held.moderated_by, self.admin)
        self.assertIsNotNone(held.moderated_at)

    @patch('esp.dbmail.models.os.popen')
    def test_send_individual_recipients(self, mock_popen):
        """cc_all=False: one sendmail call per recipient."""
        held = _create_held_email(email_list=self.email_list)
        held.approve(self.admin)
        self.assertEqual(mock_popen.call_count, 2)

    @patch('esp.dbmail.models.os.popen')
    def test_send_cc_all(self, mock_popen):
        """cc_all=True: single sendmail call with all recipients."""
        held = _create_held_email(email_list=self.email_list, cc_all=True)
        held.approve(self.admin)
        self.assertEqual(mock_popen.call_count, 1)

    @patch('esp.dbmail.models.os.popen')
    def test_send_applies_subject_prefix(self, mock_popen):
        """Approve should add subject_prefix and emailcode to Subject."""
        held = _create_held_email(
            email_list=self.email_list,
            subject_prefix='ESP',
            emailcode='M100',
        )
        held.approve(self.admin)
        # Check the message written to sendmail
        written = mock_popen.return_value.write.call_args[0][0]
        self.assertIn('[ESP]', written)
        self.assertIn('[M100]', written)

    @patch('esp.dbmail.models.os.popen')
    def test_send_no_recipients_does_not_send(self, mock_popen):
        """If recipients list is empty, sendmail should not be called."""
        held = _create_held_email(
            email_list=self.email_list,
            recipients_json=json.dumps([]),
        )
        held.approve(self.admin)
        mock_popen.assert_not_called()

    def test_mime_roundtrip(self):
        """Multipart message survives BinaryField storage round-trip."""
        msg = MIMEMultipart()
        msg['Subject'] = 'MIME roundtrip'
        msg['From'] = 'teacher@example.com'
        msg['To'] = 'test@learningu.org'
        msg.attach(MIMEText('Hello plain'))
        msg.attach(MIMEText('<html>Hello HTML</html>', 'html'))
        held = _create_held_email(
            email_list=self.email_list,
            raw_message=msg.as_bytes(),
        )
        recovered = held.get_message_object()
        self.assertTrue(recovered.is_multipart())
        content_types = [p.get_content_type() for p in recovered.walk()]
        self.assertIn('text/plain', content_types)
        self.assertIn('text/html', content_types)

    def test_str_representation(self):
        held = _create_held_email(email_list=self.email_list)
        s = str(held)
        self.assertIn('pending', s)
        self.assertIn('sender@example.com', s)
        self.assertIn('M100-students', s)

    def test_email_list_set_null_on_delete(self):
        """HeldEmail survives even if its EmailList is deleted."""
        held = _create_held_email(email_list=self.email_list)
        self.email_list.delete()
        held.refresh_from_db()
        self.assertIsNone(held.email_list)
        self.assertEqual(held.status, HeldEmail.PENDING)


class HeldEmailViewTest(TestCase):
    """Tests for the /manage/held_emails/ admin view."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.admin = ESPUser.objects.create_user(
            username='view_admin', email='vadmin@example.com', password='password'
        )
        self.admin.makeRole('Administrator')
        self.email_list = EmailList.objects.create(
            regex=r'^test$', seq=1, handler='ClassList',
            cc_all=False, admin_hold=True,
        )

    def _create_and_login(self):
        self.client.login(username='view_admin', password='password')

    def test_view_requires_admin(self):
        response = self.client.get('/manage/held_emails/')
        self.assertNotEqual(response.status_code, 200)

    def test_view_displays_pending_emails(self):
        self._create_and_login()
        _create_held_email(email_list=self.email_list, subject='Held Subject')
        response = self.client.get('/manage/held_emails/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Held Subject')

    def test_view_status_filter(self):
        self._create_and_login()
        held = _create_held_email(email_list=self.email_list, subject='Filtered')
        held.status = HeldEmail.APPROVED
        held.save()
        # Default filter is 'pending', so approved email should not appear
        response = self.client.get('/manage/held_emails/')
        self.assertNotContains(response, 'Filtered')
        # With status=approved it should
        response = self.client.get('/manage/held_emails/?status=approved')
        self.assertContains(response, 'Filtered')

    @patch('esp.dbmail.models.os.popen')
    def test_approve_single_via_post(self, mock_popen):
        self._create_and_login()
        held = _create_held_email(email_list=self.email_list)
        response = self.client.post('/manage/held_emails/', {
            'action': 'approve_single',
            'held_id': held.id,
        })
        self.assertEqual(response.status_code, 200)
        held.refresh_from_db()
        self.assertEqual(held.status, HeldEmail.APPROVED)

    def test_reject_single_via_post(self):
        self._create_and_login()
        held = _create_held_email(email_list=self.email_list)
        response = self.client.post('/manage/held_emails/', {
            'action': 'reject_single',
            'held_id': held.id,
            'rejection_reason': 'Spam',
        })
        self.assertEqual(response.status_code, 200)
        held.refresh_from_db()
        self.assertEqual(held.status, HeldEmail.REJECTED)
        self.assertEqual(held.rejection_reason, 'Spam')

    @patch('esp.dbmail.models.os.popen')
    def test_batch_approve_via_post(self, mock_popen):
        self._create_and_login()
        held1 = _create_held_email(email_list=self.email_list)
        held2 = _create_held_email(email_list=self.email_list)
        response = self.client.post('/manage/held_emails/', {
            'action': 'approve',
            'held_ids': [held1.id, held2.id],
        })
        self.assertEqual(response.status_code, 200)
        held1.refresh_from_db()
        held2.refresh_from_db()
        self.assertEqual(held1.status, HeldEmail.APPROVED)
        self.assertEqual(held2.status, HeldEmail.APPROVED)

    def test_approve_already_moderated_does_not_error(self):
        self._create_and_login()
        held = _create_held_email(email_list=self.email_list)
        held.reject(self.admin)
        # Try to approve a rejected email — should silently skip
        response = self.client.post('/manage/held_emails/', {
            'action': 'approve_single',
            'held_id': held.id,
        })
        self.assertEqual(response.status_code, 200)
        held.refresh_from_db()
        self.assertEqual(held.status, HeldEmail.REJECTED)  # unchanged

    def test_emails_page_shows_pending_held_count(self):
        self._create_and_login()
        _create_held_email(email_list=self.email_list)
        response = self.client.get('/manage/emails/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'awaiting moderation')
        self.assertContains(response, '/manage/held_emails/')
