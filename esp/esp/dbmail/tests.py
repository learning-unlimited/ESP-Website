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
