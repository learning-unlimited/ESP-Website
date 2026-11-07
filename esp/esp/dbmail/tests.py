from __future__ import absolute_import

from django.conf import settings
from django.core import mail
from django.test import TestCase

from esp.dbmail.models import send_mail


class SendMailTest(TestCase):
    def test_cc(self):
        """ cc addresses get a Cc header and are actually delivered to,
        alongside the To and Bcc recipients. """
        mail.outbox = []
        send_mail('Subject', 'Body', settings.SERVER_EMAIL, ['to@example.com'],
                  bcc=['bcc@example.com'], cc=['cc@example.com'])
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.cc, ['cc@example.com'])
        self.assertEqual(set(message.recipients()),
                         {'to@example.com', 'cc@example.com', 'bcc@example.com'})
        self.assertIn('Cc: cc@example.com', message.message().as_string())
        self.assertNotIn('bcc@example.com', message.message().as_string())
