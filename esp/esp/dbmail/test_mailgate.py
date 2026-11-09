"""Tests for esp/mailgates/mailgate.py.

The mailgate lives outside the `esp` package (Exim invokes it directly), so it is
loaded here by path rather than imported. Delivery is exercised through
MAILGATE_EMAIL_BACKEND pointed at Django's locmem backend, which captures whole
messages in `mail.outbox`.
"""
from __future__ import absolute_import

import email
import importlib.util
import os

from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.users.models import ESPUser

LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'

_MAILGATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'mailgates', 'mailgate.py')


def _load_mailgate():
    spec = importlib.util.spec_from_file_location('esp_mailgate', _MAILGATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mailgate = _load_mailgate()


def _message(frm='teacher@example.com', to='list@dev.learningu.org',
             subject='Hello', body='body line'):
    raw = ('From: %s\r\nTo: %s\r\nSubject: %s\r\n'
           'Content-Type: text/plain\r\n\r\n%s\r\n'
           % (frm, to, subject, body)).encode('utf-8')
    return email.message_from_bytes(raw, _class=mailgate._RawMIMEMessage)


class MailgateHelperTest(TestCase):
    """Helpers with no database or mail involvement."""

    def test_prefix_subject_is_idempotent(self):
        once = mailgate._prefix_subject('Hello', 'Splash')
        self.assertEqual(once, '[Splash] Hello')
        self.assertEqual(mailgate._prefix_subject(once, 'Splash'), once)

    def test_prefix_subject_ignores_case(self):
        self.assertEqual(
            mailgate._prefix_subject('Re: [SPLASH] Hello', 'Splash'),
            'Re: [SPLASH] Hello')

    def test_prefix_subject_handles_missing_subject(self):
        self.assertEqual(mailgate._prefix_subject('', 'Splash'), '[Splash]')

    def test_delivery_address_normalises_case(self):
        self.assertEqual(mailgate._delivery_address('Alice'),
                         'alice@%s' % mailgate.SITE_DOMAIN)

    def test_already_delivered_to_detects_repeat(self):
        msg = _message()
        addr = mailgate._delivery_address('alice')
        self.assertFalse(mailgate._already_delivered_to(msg, addr))
        msg[mailgate.DELIVERED_TO_HEADER] = addr
        self.assertTrue(mailgate._already_delivered_to(msg, addr))

    def test_already_delivered_to_allows_a_different_address(self):
        """Forwarding from one site address to another is not a loop."""
        msg = _message()
        msg[mailgate.DELIVERED_TO_HEADER] = mailgate._delivery_address('alice')
        self.assertFalse(
            mailgate._already_delivered_to(msg, mailgate._delivery_address('bob')))

    def test_site_address_recognises_own_domain(self):
        self.assertTrue(
            mailgate._is_site_address('someone@%s' % mailgate.SITE_DOMAIN))
        self.assertFalse(mailgate._is_site_address('someone@gmail.com'))

    def test_raw_mime_accepts_django_linesep(self):
        """Django's backends call as_bytes(linesep=...), which Message lacks."""
        out = _message().as_bytes(linesep='\r\n')
        self.assertIn(b'\r\n', out)
        self.assertIn(b'body line', out)


@override_settings(MAILGATE_EMAIL_BACKEND=LOCMEM)
class MailgateDeliveryTest(TestCase):
    """deliver() through the locmem backend."""

    def setUp(self):
        super().setUp()
        user_role_setup()
        self.teacher = ESPUser.objects.create_user(
            username='mg_teacher', email='teacher@example.com', password='pw')
        self.teacher.makeRole('Teacher')
        mail.outbox = []

    def test_one_copy_per_recipient(self):
        msg = _message()
        mailgate.deliver(msg, ['a@x.com', 'b@y.com'], False, self.teacher)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ['a@x.com'])
        self.assertEqual(mail.outbox[1].to, ['b@y.com'])
        self.assertEqual(mail.outbox[0].message()['To'], 'a@x.com')
        self.assertEqual(mail.outbox[1].message()['To'], 'b@y.com')

    def test_cc_all_sends_a_single_message(self):
        msg = _message()
        mailgate.deliver(msg, ['a@x.com', 'b@y.com'], True, self.teacher)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['a@x.com', 'b@y.com'])
        self.assertEqual(mail.outbox[0].message()['To'], 'a@x.com, b@y.com')

    def test_envelope_sender_is_the_bounce_address(self):
        mailgate.deliver(_message(), ['a@x.com'], False, self.teacher)
        self.assertEqual(mail.outbox[0].from_email, mailgate.BOUNCES)

    def test_from_is_rewritten_to_the_site_alias(self):
        """Forwarding an off-domain From fails DMARC, so it is aliased."""
        mailgate.deliver(_message(frm='teacher@example.com'), ['a@x.com'],
                         False, self.teacher)

        from_header = mail.outbox[0].message()['From']
        self.assertIn('mg_teacher@%s' % mailgate.SITE_DOMAIN, from_header)
        self.assertNotIn('teacher@example.com', from_header)

    def test_site_from_is_left_alone(self):
        """An address we can already sign for is aligned; do not touch it."""
        listaddr = 'info@%s' % mailgate.SITE_DOMAIN
        mailgate.deliver(_message(frm=listaddr), ['a@x.com'], False, self.teacher)
        self.assertIn(listaddr, mail.outbox[0].message()['From'])

    def test_off_domain_reply_to_is_removed(self):
        msg = _message()
        msg['Reply-To'] = 'teacher@example.com'
        mailgate.deliver(msg, ['a@x.com'], False, self.teacher)
        self.assertIsNone(mail.outbox[0].message()['Reply-To'])

    def test_body_is_forwarded_unchanged(self):
        mailgate.deliver(_message(body='attachment stand-in'), ['a@x.com'],
                         False, self.teacher)
        self.assertIn(b'attachment stand-in',
                      mail.outbox[0].message().as_bytes(linesep='\r\n'))


@override_settings(MAILGATE_EMAIL_BACKEND=LOCMEM,
                   EMAIL_BACKEND=LOCMEM)
class MailgateBounceTest(TestCase):
    """bounce(): who is notified, and how often."""

    def setUp(self):
        super().setUp()
        user_role_setup()
        self.user = ESPUser.objects.create_user(
            username='mg_known', email='known@example.com', password='pw')
        self.user.makeRole('Teacher')
        # Make sure to flush the cache first
        cache.clear()
        mail.outbox = []
        self.address = mailgate._delivery_address('nosuchaddress')

    def _bounce(self, frm):
        mailgate.bounce(self.address, _message(frm=frm))

    def test_registered_sender_is_notified(self):
        self._bounce('known@example.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.address, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['known@example.com'])

    def test_unregistered_sender_gets_nothing(self):
        """Bouncing would confirm which addresses exist, and could be aimed at
        a third party through a spoofed From."""
        self._bounce('stranger@evil.com')
        self.assertEqual(mail.outbox, [])

    def test_empty_from_is_ignored(self):
        mailgate.bounce(self.address, _message(frm=''))
        self.assertEqual(mail.outbox, [])

    def test_support_address_is_never_bounced_to(self):
        self._bounce(mailgate.SUPPORT)
        self.assertEqual(mail.outbox, [])

    def test_rate_limited_to_one_per_sender(self):
        """A forged From could otherwise aim a run of bounces at one user."""
        self._bounce('known@example.com')
        self._bounce('known@example.com')
        self._bounce('known@example.com')
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MAILGATE_BOUNCE_INTERVAL=0)
    def test_rate_limit_can_be_disabled(self):
        self._bounce('known@example.com')
        self._bounce('known@example.com')
        self.assertEqual(len(mail.outbox), 2)
