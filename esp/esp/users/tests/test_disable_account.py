from django.test import Client
from django.urls import reverse
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


class DisableAccountTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user, created = ESPUser.objects.get_or_create(
            username='testuser', email='test@example.com'
        )
        self.user.set_password('password')
        self.user.is_active = True
        self.user.save()
        self.client.login(username='testuser', password='password')
        self.url = reverse('disable_account')

    def test_get_does_not_mutate(self):
        """Verify that GET requests with query parameters no longer mutate state."""
        self.assertTrue(self.user.is_active)

        # Simulating the old GET vector
        response = self.client.get(self.url, {'disable': ''})
        self.assertEqual(response.status_code, 200)

        # State should not have changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_post_disable(self):
        """Verify that a valid POST with action=disable sets is_active to False."""
        self.assertTrue(self.user.is_active)

        response = self.client.post(self.url, {'action': 'disable'})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_post_enable(self):
        """Verify that a valid POST with action=enable sets is_active to True."""
        # Start with an inactive user, use force_login to bypass ModelBackend
        # which rejects inactive users in Django 2.x.
        self.user.is_active = False
        self.user.save()

        enable_client = Client()
        enable_client.force_login(self.user)

        response = enable_client.post(self.url, {'action': 'enable'})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_invalid_post_action(self):
        """Verify that invalid POST actions return 400 Bad Request."""
        response = self.client.post(self.url, {'action': 'delete_everything'})
        self.assertEqual(response.status_code, 400)

    def test_csrf_protection_enforced(self):
        """Verify that CSRF is required for POST since we did not use csrf_exempt."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser', password='password')

        # Without CSRF token in POST data
        response = csrf_client.post(self.url, {'action': 'disable'})
        self.assertEqual(response.status_code, 403)
