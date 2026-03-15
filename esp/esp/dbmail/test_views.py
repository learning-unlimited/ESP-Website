from django.contrib.auth.models import Group
from django.db.models import Q

from esp.dbmail.models import MessageRequest
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser, PersistentQueryFilter


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


def _make_message_request(creator, public=True):
    """Helper to create a minimal MessageRequest for testing."""
    recipients = PersistentQueryFilter.create_from_Q(
        item_model=ESPUser,
        q_filter=Q(id=creator.id),
        description='Test filter',
    )
    return MessageRequest.objects.create(
        subject='Test Subject',
        msgtext='Test message body',
        recipients=recipients,
        creator=creator,
        public=public,
    )


class PublicEmailViewTest(TestCase):
    """Tests for esp.dbmail.views.public_email"""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.user = ESPUser.objects.create_user(
            username='viewtestuser',
            email='viewtestuser@learningu.org',
            password='password',
        )

    def test_public_email_returns_200(self):
        """A MessageRequest with public=True should return HTTP 200."""
        msg = _make_message_request(self.user, public=True)
        response = self.client.get(f'/email/{msg.id}/')
        self.assertEqual(response.status_code, 200)

    def test_public_email_contains_subject(self):
        """The rendered page should contain the message subject."""
        msg = _make_message_request(self.user, public=True)
        response = self.client.get(f'/email/{msg.id}/')
        self.assertContains(response, 'Test Subject')

    def test_public_email_contains_body(self):
        """The rendered page should contain the message body."""
        msg = _make_message_request(self.user, public=True)
        response = self.client.get(f'/email/{msg.id}/')
        self.assertContains(response, 'Test message body')

    def test_non_public_email_raises_error(self):
        """A MessageRequest with public=False should not be accessible."""
        msg = _make_message_request(self.user, public=False)
        response = self.client.get(f'/email/{msg.id}/')
        self.assertEqual(response.status_code, 500)

    def test_nonexistent_email_id_raises_error(self):
        """A non-existent MessageRequest ID should not be accessible."""
        response = self.client.get('/email/999999/')
        self.assertEqual(response.status_code, 500)

    def test_url_without_trailing_slash(self):
        """The URL pattern allows an optional trailing slash."""
        msg = _make_message_request(self.user, public=True)
        response = self.client.get(f'/email/{msg.id}')
        self.assertIn(response.status_code, [200, 301])