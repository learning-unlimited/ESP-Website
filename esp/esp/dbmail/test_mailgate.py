"""Tests for esp/mailgates/mailgate.py.

The mailgate lives outside the `esp` package (Exim invokes it directly), so it is
loaded here by path rather than imported. Delivery is exercised through
MAILGATE_EMAIL_BACKEND pointed at Django's locmem backend, which captures whole
messages in `mail.outbox`, or through Django's real SMTP backend talking to a
fake server where address validation and SMTP refusals matter.
"""
from __future__ import absolute_import

import contextlib
import email
import importlib.util
import io
import os
import smtplib
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.mail import get_connection
from django.test import override_settings

from esp.dbmail.base import sender_account
from esp.dbmail.models import EmailList, PlainRedirect
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


def _fake_sendmail(from_addr, to_addrs, msg, *args, **kwargs):
    """Answer as smtplib does: 550 for `@refused.invalid`, 450 for `@busy.invalid`."""
    refused = {}
    for addr in to_addrs:
        if addr.endswith('@refused.invalid'):
            refused[addr] = (550, b'No such user')
        elif addr.endswith('@busy.invalid'):
            refused[addr] = (450, b'Try again later')
    if refused and len(refused) == len(to_addrs):
        raise smtplib.SMTPRecipientsRefused(refused)
    return refused


@contextlib.contextmanager
def _smtp_server():
    """Route deliver() through Django's real SMTP backend to a fake server.

    Unlike locmem, the SMTP backend parses every address, as in production.
    Yields the fake server's sendmail mock.
    """
    def connection():
        return get_connection('django.core.mail.backends.smtp.EmailBackend',
                              host='localhost', port=25, username='', password='',
                              use_tls=False, use_ssl=False)

    with patch('smtplib.SMTP') as smtp_class, \
            patch.object(mailgate, '_mail_connection', side_effect=connection):
        sendmail = smtp_class.return_value.sendmail
        sendmail.side_effect = _fake_sendmail
        yield sendmail


def _envelopes(sendmail):
    """The envelope recipients of each message the fake server was handed."""
    return [call.args[1] for call in sendmail.call_args_list]


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


class MailgateSMTPTest(TestCase):
    """deliver() through Django's SMTP backend: addresses and refusals."""

    def setUp(self):
        super().setUp()
        user_role_setup()
        self.teacher = ESPUser.objects.create_user(
            username='mg_smtp', email='smtp@example.com', password='pw')
        self.teacher.makeRole('Teacher')

    def _deliver(self, recipients, cc_all=False):
        with _smtp_server() as sendmail:
            delivered = mailgate.deliver(_message(), recipients, cc_all, self.teacher)
        return delivered, _envelopes(sendmail)

    def test_comma_separated_destination_is_split(self):
        """A PlainRedirect may list several destinations in one entry."""
        delivered, envelopes = self._deliver(['a@x.com, b@y.com'])
        self.assertEqual(delivered, ['a@x.com', 'b@y.com'])
        self.assertEqual(envelopes, [['a@x.com'], ['b@y.com']])

    def test_malformed_address_does_not_block_cc_all(self):
        delivered, envelopes = self._deliver(
            ['valid@example.com', 'also@example.com, not-an-address'], cc_all=True)
        self.assertEqual(delivered, ['valid@example.com', 'also@example.com'])
        self.assertEqual(envelopes, [['valid@example.com', 'also@example.com']])

    def test_internationalized_domain_is_punycoded(self):
        """formataddr rejects non-ASCII addresses, which once dropped the whole list."""
        delivered, envelopes = self._deliver(['user@bücher.de', 'b@y.com'], cc_all=True)
        self.assertEqual(delivered, ['user@xn--bcher-kva.de', 'b@y.com'])
        self.assertEqual(envelopes, [['user@xn--bcher-kva.de', 'b@y.com']])

    def test_unicode_display_name_is_kept(self):
        self.assertEqual(mailgate._split_recipients(['José <j@x.com>']),
                         ['=?utf-8?b?Sm9zw6k=?= <j@x.com>'])

    def test_permanently_refused_recipient_is_skipped(self):
        """Raising would make the MTA retry, duplicating earlier copies and
        never reaching later recipients."""
        delivered, envelopes = self._deliver(
            ['a@x.com', 'gone@refused.invalid', 'b@y.com'])
        self.assertEqual(delivered, ['a@x.com', 'b@y.com'])
        self.assertEqual(len(envelopes), 3)

    def test_all_recipients_refused_delivers_nothing(self):
        delivered, _envelopes = self._deliver(['gone@refused.invalid'])
        self.assertEqual(delivered, [])

    def test_temporary_refusal_is_retried(self):
        """A 4xx refusal must reach the MTA's retry path, not be skipped."""
        with self.assertRaises(smtplib.SMTPRecipientsRefused):
            self._deliver(['a@x.com', 'full@busy.invalid'])


@override_settings(MAILGATE_EMAIL_BACKEND=LOCMEM)
class SenderAccountTest(TestCase):
    """sender_account(): which From addresses resolve to an account."""

    def setUp(self):
        super().setUp()
        user_role_setup()
        self.teacher = ESPUser.objects.create_user(
            username='mg_sender', email='sender@example.com', password='pw')
        self.teacher.makeRole('Teacher')
        mail.outbox = []

    def test_personal_address_resolves(self):
        self.assertEqual(sender_account(_message(frm='Sender@Example.com')),
                         self.teacher)

    def test_site_alias_resolves(self):
        frm = 'MG_Sender@%s' % mailgate.SITE_DOMAIN
        self.assertEqual(sender_account(_message(frm=frm)), self.teacher)

    def test_alias_on_another_domain_does_not_resolve(self):
        """Usernames are per site, so another chapter's alias is someone else."""
        self.assertIsNone(sender_account(_message(frm='mg_sender@other.learningu.org')))

    def test_unknown_sender_does_not_resolve(self):
        self.assertIsNone(sender_account(_message(frm='stranger@evil.com')))

    def test_forwarded_message_still_resolves_on_second_hop(self):
        """A redirect to another site address re-enters the mailgate with the
        From already rewritten to the sender's alias."""
        mailgate.deliver(_message(frm='sender@example.com'),
                         ['other@%s' % mailgate.SITE_DOMAIN], False, self.teacher)

        raw = mail.outbox[0].message().as_bytes(linesep='\r\n')
        second_hop = email.message_from_bytes(raw, _class=mailgate._RawMIMEMessage)
        self.assertEqual(sender_account(second_hop), self.teacher)


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

    def _bounce(self, sender_email):
        mailgate.bounce(self.address, sender_email)

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

    def test_empty_sender_is_ignored(self):
        self._bounce('')
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


@override_settings(EMAIL_BACKEND=LOCMEM)
class MailgateMainTest(TestCase):
    """main() end to end: routing, sender checks and bounces."""

    def setUp(self):
        super().setUp()
        user_role_setup()
        self.teacher = ESPUser.objects.create_user(
            username='mg_main', email='main@example.com', password='pw')
        self.teacher.makeRole('Teacher')
        # The default routes, as created by the dbmail migrations
        for seq, handler in ((30, 'PlainList'), (40, 'UserEmail')):
            if not EmailList.objects.filter(handler=handler).exists():
                EmailList.objects.create(regex=r'^(.*)$', seq=seq, handler=handler)
        PlainRedirect.objects.create(original='directors',
                                     destination='a@x.com, b@y.com')
        PlainRedirect.objects.create(original='gone',
                                     destination='gone@refused.invalid')
        cache.clear()
        mail.outbox = []

    def _run(self, local_part, frm='main@example.com'):
        raw = _message(frm=frm).as_bytes()
        with patch.dict(os.environ, {'LOCAL_PART': local_part}), \
                patch.object(mailgate.sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw))), \
                _smtp_server() as sendmail:
            mailgate.main()
        return _envelopes(sendmail)

    def test_redirect_reaches_every_destination(self):
        self.assertEqual(self._run('Directors'), [['a@x.com'], ['b@y.com']])
        self.assertEqual(mail.outbox, [])

    def test_unregistered_sender_is_not_forwarded(self):
        self.assertEqual(self._run('directors', frm='stranger@evil.com'), [])
        self.assertEqual(mail.outbox, [])

    def test_empty_from_is_not_forwarded(self):
        self.assertEqual(self._run('directors', frm=''), [])
        self.assertEqual(mail.outbox, [])

    def test_malformed_from_is_not_forwarded(self):
        self.assertEqual(self._run('directors', frm='not an address'), [])
        self.assertEqual(mail.outbox, [])

    def test_unknown_address_bounces_to_sender(self):
        self.assertEqual(self._run('nosuchaddress'), [])
        self.assertEqual([m.to for m in mail.outbox], [['main@example.com']])

    def test_refused_delivery_bounces_to_account_address(self):
        """By the time the bounce is sent, From has been rewritten to the
        sender's site alias, which matches no stored email."""
        self._run('gone')
        self.assertEqual([m.to for m in mail.outbox], [['main@example.com']])
