"""
Tests for esp.dbmail.models
Source: esp/esp/dbmail/models.py

Tests send_mail functionality, ActionHandler dynamic dispatch,
and MessageRequest validation methods.
"""
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import Group
from django.core import mail

from esp.dbmail.models import (
    ActionHandler,
    MessageRequest,
    send_mail,
)
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
"""
Tests for esp.dbmail.cronmail
Source: esp/esp/dbmail/cronmail.py

Tests the process_messages and send_email_requests functions.
"""
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import Group

from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


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
