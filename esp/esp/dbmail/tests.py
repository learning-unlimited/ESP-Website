from __future__ import absolute_import

from django.test import SimpleTestCase

from email.message import Message

from esp.dbmail.mailgate_utils import sanitize_recipient_headers


class MailgateUtilsTest(SimpleTestCase):
    def _msg(self, to=None, cc=None, bcc=None):
        msg = Message()
        if to is not None:
            msg["To"] = to
        if cc is not None:
            msg["Cc"] = cc
        if bcc is not None:
            msg["Bcc"] = bcc
        return msg

    def test_removes_self_references_from_headers(self):
        msg = self._msg(
            to='Class List <math101-class@test.learningu.org>, other@test.learningu.org',
            cc='math101-class@test.learningu.org, cc@example.com',
            bcc='math101-class@test.learningu.org, bcc@example.com',
        )
        sanitize_recipient_headers(
            msg,
            local_part='math101-class',
            domain='test.learningu.org',
            drop_bcc=False,
        )

        self.assertEqual(msg.get("To"), "other@test.learningu.org")
        self.assertEqual(msg.get("Cc"), "cc@example.com")
        self.assertEqual(msg.get("Bcc"), "bcc@example.com")

    def test_drops_bcc_for_forwarded_mail(self):
        msg = self._msg(
            to='other@test.learningu.org',
            bcc='math101-class@test.learningu.org, hidden@example.com',
        )
        sanitize_recipient_headers(
            msg,
            local_part='math101-class',
            domain='test.learningu.org',
            drop_bcc=True,
        )

        self.assertEqual(msg.get("To"), "other@test.learningu.org")
        self.assertIsNone(msg.get("Bcc"))

    def test_deletes_header_when_only_self_address_present(self):
        msg = self._msg(to='math101-class@test.learningu.org')
        sanitize_recipient_headers(
            msg,
            local_part='math101-class',
            domain='test.learningu.org',
            drop_bcc=False,
        )
        self.assertIsNone(msg.get("To"))
