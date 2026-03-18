"""
Tests for email preview functionality
"""

from django.core import mail
from django.db.models import Q

from esp.dbmail.models import MessageRequest
from esp.tests.util import CacheFlushTestCase
from esp.users.models import ESPUser, PersistentQueryFilter


def _setup_roles():
    from django.contrib.auth.models import Group
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class EmailPreviewViewTestCase(CacheFlushTestCase):
    """Test cases for email preview view"""

    def setUp(self):
        super().setUp()
        _setup_roles()

        # Create test users
        self.admin_user = ESPUser.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        self.admin_user.makeRole('Administrator')

        self.recipient_user = ESPUser.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

        # Create a recipient filter using a Q object (correct usage)
        self.filter = PersistentQueryFilter.create_from_Q(
            item_model=ESPUser,
            q_filter=Q(id=self.recipient_user.id),
            description='Test Filter'
        )

        # Create a test message request with template variables via createRequest
        # so that parseSmartText has access to the user variable
        self.msg_req = MessageRequest.createRequest(
            var_dict={'user': self.recipient_user},
            subject='Welcome {{user.first_name}}!',
            msgtext='Hello {{user.first_name}} {{user.last_name}}, welcome to our program.',
            sender='noreply@example.com',
            creator=self.admin_user,
            recipients=self.filter
        )
        self.msg_req.save()

    def test_preview_email_requires_login(self):
        """Test that preview requires authentication"""
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        # Should redirect to login (302)
        self.assertEqual(response.status_code, 302)

    def test_preview_email_with_authenticated_user(self):
        """Test preview view with authenticated admin user"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)

    def test_preview_renders_template_variables(self):
        """Test that template variables are properly rendered"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        content = response.content.decode()
        self.assertIn('Welcome John!', content)
        self.assertIn('Hello John Doe', content)

    def test_preview_shows_correct_sender(self):
        """Test that preview displays correct sender"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        self.assertIn('noreply@example.com', response.content.decode())

    def test_preview_shows_recipient_count(self):
        """Test that preview shows correct recipient count"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        self.assertIn('1 recipient', response.content.decode())

    def test_preview_with_nonexistent_message(self):
        """Test preview with invalid message request ID"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/99999/')
        self.assertEqual(response.status_code, 404)

    def test_preview_uses_sample_user_data(self):
        """Test that preview uses first recipient as sample"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        content = response.content.decode()
        self.assertIn('John', content)
        self.assertIn('recipient', content)


class SendTestEmailViewTestCase(CacheFlushTestCase):
    """Test cases for send test email view"""

    def setUp(self):
        super().setUp()
        _setup_roles()

        # Create test user
        self.admin_user = ESPUser.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        self.admin_user.makeRole('Administrator')

        # Create recipient filter using a Q object
        self.filter = PersistentQueryFilter.create_from_Q(
            item_model=ESPUser,
            q_filter=Q(id=self.admin_user.id),
            description='Test Filter'
        )

        # Create message request via createRequest
        self.msg_req = MessageRequest.createRequest(
            var_dict={'user': self.admin_user},
            subject='Test Subject {{user.first_name}}',
            msgtext='Hello {{user.first_name}}, this is a test.',
            sender='noreply@example.com',
            creator=self.admin_user,
            recipients=self.filter
        )
        self.msg_req.save()

    def test_send_test_email_requires_login(self):
        """Test that send test requires authentication"""
        response = self.client.post('/dbmail/send_test/{}/'.format(self.msg_req.id))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login', response.url)

    def test_send_test_email_requires_post(self):
        """Test that send test only accepts POST"""
        self.client.force_login(self.admin_user)
        response = self.client.get('/dbmail/send_test/{}/'.format(self.msg_req.id))
        # Should redirect with error (GET not allowed)
        self.assertEqual(response.status_code, 302)

    def test_send_test_email_sends_to_admin(self):
        """Test that test email is sent to admin's address"""
        self.client.force_login(self.admin_user)
        mail.outbox = []
        self.client.post('/dbmail/send_test/{}/'.format(self.msg_req.id))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('admin@example.com', mail.outbox[0].to)

    def test_send_test_email_renders_variables(self):
        """Test that test email renders template variables"""
        self.client.force_login(self.admin_user)
        mail.outbox = []
        self.client.post('/dbmail/send_test/{}/'.format(self.msg_req.id))
        self.assertIn('Test Subject Admin', mail.outbox[0].subject)
        self.assertIn('Hello Admin', mail.outbox[0].body)

    def test_send_test_email_redirects_to_preview(self):
        """Test that after sending, redirects back to preview"""
        self.client.force_login(self.admin_user)
        response = self.client.post('/dbmail/send_test/{}/'.format(self.msg_req.id))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/preview/{}/'.format(self.msg_req.id), response.url)

    def test_send_test_email_with_nonexistent_message(self):
        """Test send test with invalid message ID"""
        self.client.force_login(self.admin_user)
        response = self.client.post('/dbmail/send_test/99999/')
        self.assertEqual(response.status_code, 404)


class EmailPreviewIntegrationTestCase(CacheFlushTestCase):
    """Integration tests for email preview feature"""

    def setUp(self):
        super().setUp()
        _setup_roles()

        self.admin = ESPUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            first_name='Admin'
        )
        self.admin.makeRole('Administrator')

        self.user1 = ESPUser.objects.create_user(
            username='user1',
            email='user1@test.com',
            first_name='Alice'
        )

        self.user2 = ESPUser.objects.create_user(
            username='user2',
            email='user2@test.com',
            first_name='Bob'
        )

        # Create filter with multiple recipients using Q object
        self.filter = PersistentQueryFilter.create_from_Q(
            item_model=ESPUser,
            q_filter=Q(username__in=['user1', 'user2']),
            description='Multiple Recipients'
        )

        self.msg_req = MessageRequest.createRequest(
            var_dict={'user': self.user1},
            subject='Announcement for {{user.first_name}}',
            msgtext='Dear {{user.first_name}}, this is an announcement.',
            creator=self.admin,
            recipients=self.filter
        )
        self.msg_req.save()

    def test_preview_with_multiple_recipients(self):
        """Test preview shows correct count with multiple recipients"""
        self.client.force_login(self.admin)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        self.assertIn('2 recipient', response.content.decode())

    def test_preview_uses_first_recipient_as_sample(self):
        """Test that preview uses first recipient for sample"""
        self.client.force_login(self.admin)
        response = self.client.get('/dbmail/preview/{}/'.format(self.msg_req.id))
        content = response.content.decode()
        self.assertTrue('Alice' in content or 'Bob' in content)
