from django.test import TestCase, Client
from django.urls import reverse
from esp.users.models import ESPUser

class LoginOpenRedirectTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user and log them in
        self.user = ESPUser.objects.create_user(username='redirect_tester', password='securepassword123')
        self.client.login(username='redirect_tester', password='securepassword123')
        self.login_url = reverse('login')

    def test_authenticated_login_external_redirect_blocked(self):
        """Test that passing an external URL in the 'next' parameter falls back safely."""
        malicious_url = "http://evil-phishing-site.com/login"
        response = self.client.get(f"{self.login_url}?next={malicious_url}")

        # The system uses HttpMetaRedirect, so it returns a 200 OK with a meta tag
        self.assertEqual(response.status_code, 200)
        
        # Prove the malicious URL was stripped out of the response
        response_content = response.content.decode()
        self.assertNotIn(malicious_url, response_content)
        
        # Prove it fell back to a safe internal route (usually '/' or '/myesp/profile')
        self.assertTrue('url=/' in response_content or 'url=/myesp/profile' in response_content)

    def test_authenticated_login_javascript_redirect_blocked(self):
        """Test that passing a javascript: protocol in the 'next' parameter is blocked."""
        malicious_url = "javascript:alert('XSS_ATTACK')"
        response = self.client.get(f"{self.login_url}?next={malicious_url}")

        self.assertEqual(response.status_code, 200)
        
        # Prove the JS payload was stripped out
        self.assertNotIn(malicious_url, response.content.decode())

class SignoutOpenRedirectTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signout_url = reverse('signout')

    def test_signout_external_redirect_blocked(self):
        """Test that passing an external URL in the 'redirect' parameter falls back safely."""
        malicious_url = "http://evil-phishing-site.com"
        response = self.client.get(f"{self.signout_url}?redirect={malicious_url}")

        # The view should block the redirect and return the standard 200 OK logged-out page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/logged_out.html')

    def test_signout_safe_redirect_allowed(self):
        """Test that passing a safe internal URL in the 'redirect' parameter works."""
        safe_url = "/myesp/profile"
        response = self.client.get(f"{self.signout_url}?redirect={safe_url}")

        # The view should allow the redirect because it is an internal path
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, safe_url)
