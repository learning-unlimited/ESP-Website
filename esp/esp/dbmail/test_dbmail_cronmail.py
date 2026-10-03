from __future__ import absolute_import

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase, override_settings

from esp.dbmail.cronmail import send_email_requests


class MockQuerySet(object):
    """Mock QuerySet supporting count(), slicing, and iterator() for batch testing."""

    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def __getitem__(self, val):
        if isinstance(val, slice):
            return MockQuerySet(self.items[val])
        return self.items[val]

    def iterator(self):
        return iter(self.items)


class MockTextOfEmail(object):
    """Mock TextOfEmail object with configurable send() behavior."""

    def __init__(self, email_id, send_from, send_to, subject, exception=None):
        self.id = email_id
        self.send_from = send_from
        self.send_to = send_to
        self.subject = subject
        self.exception = exception

    def send(self):
        return self.exception


class CronmailSendEmailRequestsTest(TestCase):
    """Tests for send_email_requests() in esp.dbmail.cronmail."""

    @patch('esp.dbmail.cronmail.send_mail')
    @patch('esp.dbmail.cronmail.TextOfEmail.objects.filter')
    def test_delivery_failure_sent_to_failed_email_sender(self, mock_filter, mock_send_mail):
        """
        Verify that when an email from sender1 fails and a subsequent email from
        sender2 succeeds, the delivery failure notification is sent to sender1,
        NOT to sender2 (fixing loop variable leakage).
        """
        mail1 = MockTextOfEmail(
            email_id=1,
            send_from='sender1@example.com',
            send_to='recipient1@example.com',
            subject='Failed Message',
            exception=RuntimeError('SMTP connection refused'),
        )
        mail2 = MockTextOfEmail(
            email_id=2,
            send_from='sender2@example.com',
            send_to='recipient2@example.com',
            subject='Successful Message',
            exception=None,
        )
        mock_filter.return_value = MockQuerySet([mail1, mail2])

        send_email_requests()

        # send_mail should have been called for mail delivery failure
        failure_calls = [
            call for call in mock_send_mail.call_args_list
            if call[0][0] == 'Mail delivery failure'
        ]
        self.assertEqual(len(failure_calls), 1)

        args, _ = failure_calls[0]
        subject, body, from_email, recipients = args

        # The failure notification must be sent to sender1, NOT sender2
        self.assertIn('sender1@example.com', recipients)
        self.assertNotIn('sender2@example.com', recipients)
        self.assertIn('Failed Message', body)
        self.assertNotIn('Successful Message', body)

    @patch('esp.dbmail.cronmail.send_mail')
    @patch('esp.dbmail.cronmail.TextOfEmail.objects.filter')
    def test_multiple_senders_receive_separate_failure_notices(self, mock_filter, mock_send_mail):
        """
        Verify that when failures occur across multiple senders, each sender
        receives only their respective failure report.
        """
        mail1 = MockTextOfEmail(
            email_id=1,
            send_from='alice@example.com',
            send_to='dest1@example.com',
            subject='Alice Message',
            exception=RuntimeError('Mailbox full'),
        )
        mail2 = MockTextOfEmail(
            email_id=2,
            send_from='bob@example.com',
            send_to='dest2@example.com',
            subject='Bob Message',
            exception=RuntimeError('Host unreachable'),
        )
        mock_filter.return_value = MockQuerySet([mail1, mail2])

        send_email_requests()

        failure_calls = [
            call for call in mock_send_mail.call_args_list
            if call[0][0] == 'Mail delivery failure'
        ]
        self.assertEqual(len(failure_calls), 2)

        # Map each recipient to the body content of their notification
        notifications = {}
        for call in failure_calls:
            args, _ = call
            recipients = args[3]
            body = args[1]
            for r in recipients:
                notifications[r] = body

        self.assertIn('alice@example.com', notifications)
        self.assertIn('Alice Message', notifications['alice@example.com'])
        self.assertNotIn('Bob Message', notifications['alice@example.com'])

        self.assertIn('bob@example.com', notifications)
        self.assertIn('Bob Message', notifications['bob@example.com'])
        self.assertNotIn('Alice Message', notifications['bob@example.com'])

    @patch('esp.dbmail.cronmail.send_mail')
    @patch('esp.dbmail.cronmail.TextOfEmail.objects.filter')
    def test_same_sender_multiple_failures_grouped(self, mock_filter, mock_send_mail):
        """
        Verify that multiple failures from the same sender are grouped into
        a single delivery failure notification.
        """
        mail1 = MockTextOfEmail(
            email_id=1,
            send_from='teacher@example.com',
            send_to='student1@example.com',
            subject='Class Update 1',
            exception=RuntimeError('Bounce'),
        )
        mail2 = MockTextOfEmail(
            email_id=2,
            send_from='teacher@example.com',
            send_to='student2@example.com',
            subject='Class Update 2',
            exception=RuntimeError('Bounce'),
        )
        mock_filter.return_value = MockQuerySet([mail1, mail2])

        send_email_requests()

        failure_calls = [
            call for call in mock_send_mail.call_args_list
            if call[0][0] == 'Mail delivery failure'
        ]
        self.assertEqual(len(failure_calls), 1)

        args, _ = failure_calls[0]
        body = args[1]
        recipients = args[3]

        self.assertEqual(recipients[0], 'teacher@example.com')
        self.assertIn('Class Update 1', body)
        self.assertIn('Class Update 2', body)

    @override_settings(DEFAULT_EMAIL_ADDRESSES={'bounces': 'bounces@example.com'})
    @patch('esp.dbmail.cronmail.send_mail')
    @patch('esp.dbmail.cronmail.TextOfEmail.objects.filter')
    def test_bounces_address_included_when_configured(self, mock_filter, mock_send_mail):
        """
        Verify that the default bounce address is included in recipients
        when configured in settings.DEFAULT_EMAIL_ADDRESSES.
        """
        mail = MockTextOfEmail(
            email_id=10,
            send_from='organizer@example.com',
            send_to='student@example.com',
            subject='Program Notice',
            exception=RuntimeError('SMTP error'),
        )
        mock_filter.return_value = MockQuerySet([mail])

        send_email_requests()

        failure_calls = [
            call for call in mock_send_mail.call_args_list
            if call[0][0] == 'Mail delivery failure'
        ]
        self.assertEqual(len(failure_calls), 1)

        recipients = failure_calls[0][0][3]
        self.assertIn('organizer@example.com', recipients)
        self.assertIn('bounces@example.com', recipients)

    @patch('esp.dbmail.cronmail.send_mail')
    @patch('esp.dbmail.cronmail.TextOfEmail.objects.filter')
    def test_all_successful_sends_no_failure_notifications(self, mock_filter, mock_send_mail):
        """
        Verify that no failure notification is dispatched when all emails send successfully.
        """
        mail1 = MockTextOfEmail(1, 's1@example.com', 'd1@example.com', 'Sub 1', None)
        mail2 = MockTextOfEmail(2, 's2@example.com', 'd2@example.com', 'Sub 2', None)
        mock_filter.return_value = MockQuerySet([mail1, mail2])

        send_email_requests()

        failure_calls = [
            call for call in mock_send_mail.call_args_list
            if call[0][0] == 'Mail delivery failure'
        ]
        self.assertEqual(len(failure_calls), 0)
