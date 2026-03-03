from __future__ import absolute_import

from django.test import TestCase, Client
from django.db.models import Q

from esp.users.models import ESPUser, PersistentQueryFilter
from esp.dbmail.models import MessageRequest


class MessageRequestAdminTest(TestCase):
    """
    Tests for the MessageRequest Django admin form.

    Regression test for issue #1983: the admin was complaining that
    sendto_fn_name and processed_by were required even when valid values
    were provided.
    """

    def setUp(self):
        self.client = Client()

        # Create an admin user
        self.admin = ESPUser.objects.create_superuser(
            username='test_admin',
            email='admin@test.com',
            password='password',
        )

        # Create a PersistentQueryFilter (required FK on MessageRequest)
        self.recipients = PersistentQueryFilter.create_from_Q(
            item_model=ESPUser,
            q_filter=Q(id=self.admin.id),
            description='Test filter',
        )

        self.client.login(username='test_admin', password='password')

    def _post_messagerequest(self, extra_data=None):
        """POST to the admin add view for MessageRequest."""
        data = {
            'subject': 'Test subject',
            'msgtext': 'Test message',
            'special_headers': '',
            'recipients': self.recipients.id,
            'sendto_fn_name': '',   # SEND_TO_SELF — the problematic empty value
            'sender': '',
            'creator': self.admin.id,
            'processed': False,
            'processed_by': '',     # nullable datetime — left blank
            'priority_level': '',
            'public': False,
        }
        if extra_data:
            data.update(extra_data)
        return self.client.post('/admin/dbmail/messagerequest/add/', data, follow=True)

    def test_sendto_fn_name_blank_is_valid(self):
        """
        Submitting sendto_fn_name='' ("send to user") should not raise a
        "This field is required" error in the admin.
        """
        response = self._post_messagerequest()
        # A successful save redirects to the changelist; no form errors
        self.assertNotIn(b'This field is required', response.content)
        self.assertTrue(MessageRequest.objects.filter(subject='Test subject').exists())

    def test_processed_by_blank_is_valid(self):
        """
        Leaving processed_by empty should not raise a "This field is required"
        error in the admin, since the field is nullable.
        """
        response = self._post_messagerequest()
        self.assertNotIn(b'This field is required', response.content)
        mr = MessageRequest.objects.filter(subject='Test subject').first()
        self.assertIsNotNone(mr)
        self.assertIsNone(mr.processed_by)
