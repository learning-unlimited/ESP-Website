"""
Tests for email preview functionality
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from esp.dbmail.models import MessageRequest
from esp.dbmail.views import preview_email, send_test_email
from esp.users.models import ESPUser, PersistentQueryFilter


class EmailPreviewViewTestCase(TestCase):
    """Test cases for email preview view"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test users
        self.admin_user = ESPUser.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        
        self.recipient_user = ESPUser.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        # Create a recipient filter
        self.filter = PersistentQueryFilter.create_from_Q(
            ESPUser.objects.filter(id=self.recipient_user.id),
            'Test Filter'
        )
        
        # Create a test message request with template variables
        self.msg_req = MessageRequest.objects.create(
            subject='Welcome {{user.first_name}}!',
            msgtext='Hello {{user.first_name}} {{user.last_name}}, welcome to our program.',
            sender='noreply@example.com',
            creator=self.admin_user,
            recipients=self.filter
        )
    
    def test_preview_email_requires_login(self):
        """Test that preview requires authentication"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = AnonymousUser()
        
        response = preview_email(request, self.msg_req.id)
        
        # Should redirect to login (302)
        self.assertEqual(response.status_code, 302)
    
    def test_preview_email_with_authenticated_user(self):
        """Test preview view with authenticated user"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin_user
        
        response = preview_email(request, self.msg_req.id)
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
    
    def test_preview_renders_template_variables(self):
        """Test that template variables are properly rendered"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin_user
        
        response = preview_email(request, self.msg_req.id)
        
        # Check that template variables were rendered
        self.assertIn('Welcome John!', response.content.decode())
        self.assertIn('Hello John Doe', response.content.decode())
    
    def test_preview_shows_correct_sender(self):
        """Test that preview displays correct sender"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin_user
        
        response = preview_email(request, self.msg_req.id)
        
        # Should show the sender from message request
        self.assertIn('noreply@example.com', response.content.decode())
    
    def test_preview_shows_recipient_count(self):
        """Test that preview shows correct recipient count"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin_user
        
        response = preview_email(request, self.msg_req.id)
        
        # Should show 1 recipient
        self.assertIn('1 recipient', response.content.decode())
    
    def test_preview_with_nonexistent_message(self):
        """Test preview with invalid message request ID"""
        request = self.factory.get('/dbmail/preview/99999/')
        request.user = self.admin_user
        
        # Should raise 404
        from django.http import Http404
        with self.assertRaises(Http404):
            preview_email(request, 99999)
    
    def test_preview_uses_sample_user_data(self):
        """Test that preview uses first recipient as sample"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin_user
        
        response = preview_email(request, self.msg_req.id)
        
        # Should use recipient_user's data (John Doe)
        self.assertIn('John', response.content.decode())
        self.assertIn('recipient', response.content.decode())


class SendTestEmailViewTestCase(TestCase):
    """Test cases for send test email view"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test user
        self.admin_user = ESPUser.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        
        # Create recipient filter
        self.filter = PersistentQueryFilter.create_from_Q(
            ESPUser.objects.filter(id=self.admin_user.id),
            'Test Filter'
        )
        
        # Create message request
        self.msg_req = MessageRequest.objects.create(
            subject='Test Subject {{user.first_name}}',
            msgtext='Hello {{user.first_name}}, this is a test.',
            sender='test@example.com',
            creator=self.admin_user,
            recipients=self.filter
        )
    
    def _add_messages_to_request(self, request):
        """Helper to add messages framework to request"""
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request
    
    def test_send_test_email_requires_login(self):
        """Test that send test requires authentication"""
        request = self.factory.post(f'/dbmail/send_test/{self.msg_req.id}/')
        request.user = AnonymousUser()
        
        response = send_test_email(request, self.msg_req.id)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_send_test_email_requires_post(self):
        """Test that send test only accepts POST"""
        request = self.factory.get(f'/dbmail/send_test/{self.msg_req.id}/')
        request.user = self.admin_user
        request = self._add_messages_to_request(request)
        
        response = send_test_email(request, self.msg_req.id)
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
    
    def test_send_test_email_sends_to_admin(self):
        """Test that test email is sent to admin's address"""
        request = self.factory.post(f'/dbmail/send_test/{self.msg_req.id}/')
        request.user = self.admin_user
        request = self._add_messages_to_request(request)
        
        # Clear mail outbox
        mail.outbox = []
        
        response = send_test_email(request, self.msg_req.id)
        
        # Should send one email
        self.assertEqual(len(mail.outbox), 1)
        
        # Email should be sent to admin
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])
    
    def test_send_test_email_renders_variables(self):
        """Test that test email renders template variables"""
        request = self.factory.post(f'/dbmail/send_test/{self.msg_req.id}/')
        request.user = self.admin_user
        request = self._add_messages_to_request(request)
        
        mail.outbox = []
        
        send_test_email(request, self.msg_req.id)
        
        # Check email content has rendered variables
        self.assertIn('Test Subject Admin', mail.outbox[0].subject)
        self.assertIn('Hello Admin', mail.outbox[0].body)
    
    def test_send_test_email_redirects_to_preview(self):
        """Test that after sending, redirects back to preview"""
        request = self.factory.post(f'/dbmail/send_test/{self.msg_req.id}/')
        request.user = self.admin_user
        request = self._add_messages_to_request(request)
        
        response = send_test_email(request, self.msg_req.id)
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        # Should redirect to preview page
        self.assertIn(f'/preview/{self.msg_req.id}/', response.url)
    
    def test_send_test_email_with_nonexistent_message(self):
        """Test send test with invalid message ID"""
        request = self.factory.post('/dbmail/send_test/99999/')
        request.user = self.admin_user
        request = self._add_messages_to_request(request)
        
        from django.http import Http404
        with self.assertRaises(Http404):
            send_test_email(request, 99999)


class EmailPreviewIntegrationTestCase(TestCase):
    """Integration tests for email preview feature"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create multiple users
        self.admin = ESPUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            first_name='Admin'
        )
        
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
        
        # Create filter with multiple recipients
        self.filter = PersistentQueryFilter.create_from_Q(
            ESPUser.objects.filter(username__in=['user1', 'user2']),
            'Multiple Recipients'
        )
        
        self.msg_req = MessageRequest.objects.create(
            subject='Announcement for {{user.first_name}}',
            msgtext='Dear {{user.first_name}}, this is an announcement.',
            creator=self.admin,
            recipients=self.filter
        )
    
    def test_preview_with_multiple_recipients(self):
        """Test preview shows correct count with multiple recipients"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin
        
        response = preview_email(request, self.msg_req.id)
        
        # Should show 2 recipients
        self.assertIn('2 recipient', response.content.decode())
    
    def test_preview_uses_first_recipient_as_sample(self):
        """Test that preview uses first recipient for sample"""
        request = self.factory.get(f'/dbmail/preview/{self.msg_req.id}/')
        request.user = self.admin
        
        response = preview_email(request, self.msg_req.id)
        
        # Should use first recipient (Alice or Bob)
        content = response.content.decode()
        self.assertTrue('Alice' in content or 'Bob' in content)
