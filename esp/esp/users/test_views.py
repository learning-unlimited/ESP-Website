"""
Regression tests for the redirect handling in esp.users.views.

Covers the three issues reported in #4590:
  - HttpMetaRedirect must escape its location so it cannot inject markup.
  - CustomLoginView.handle_authenticated_user must not honor a ?next= that
    points off-site.
  - signout() must not honor a ?redirect= that points off-site.
"""

from django.test import SimpleTestCase
from django.urls import reverse

from esp.program.models import RegistrationProfile
from esp.tests.util import CacheFlushTestCase
from esp.users.models import ESPUser
from esp.users.views import HttpMetaRedirect

EXTERNAL_URL = 'http://evil-phishing-site.example.com/login'


class HttpMetaRedirectEscapingTest(SimpleTestCase):
    """ HttpMetaRedirect interpolates its location into HTML by hand. """

    def test_location_is_escaped(self):
        payload = '/myesp/profile"><script>alert("XSS")</script>'
        content = HttpMetaRedirect(payload).content.decode()

        # The payload must not survive as markup, in the meta tag or the link
        self.assertNotIn(payload, content)
        self.assertNotIn('<script>', content)
        self.assertIn('&quot;', content)
        self.assertIn('&lt;script&gt;', content)

    def test_safe_location_is_left_alone(self):
        content = HttpMetaRedirect('/myesp/profile').content.decode()
        self.assertIn('url=/myesp/profile"', content)


class LoginRedirectTest(CacheFlushTestCase):
    """ ?next= handling for a user who is already logged in.

    The user needs a RegistrationProfile: without one,
    handle_authenticated_user() short-circuits to /myesp/profile and never
    looks at ?next= at all.  The user is deliberately left without a role
    Group so that mask_redirect() falls through to '/' rather than to one
    of the *_home_page Tags.
    """

    def setUp(self):
        super().setUp()
        self.user = ESPUser.objects.create_user(username='redirect_tester',
                                                password='password')
        RegistrationProfile.objects.create(user=self.user)
        self.assertTrue(self.client.login(username='redirect_tester',
                                          password='password'))
        self.login_url = reverse('login')

    def get_next(self, next_url):
        """ GET the login page as an authenticated user, return the body. """
        response = self.client.get(self.login_url, {'next': next_url})
        # The view answers with HttpMetaRedirect, i.e. a 200 with a meta tag
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_external_next_falls_back_to_safe_location(self):
        content = self.get_next(EXTERNAL_URL)
        self.assertNotIn('evil-phishing-site.example.com', content)
        self.assertIn('url=/"', content)

    def test_protocol_relative_next_falls_back_to_safe_location(self):
        content = self.get_next('//evil-phishing-site.example.com')
        self.assertNotIn('evil-phishing-site.example.com', content)
        self.assertIn('url=/"', content)

    def test_javascript_next_falls_back_to_safe_location(self):
        content = self.get_next("javascript:alert('XSS')")
        self.assertNotIn('javascript:', content)
        self.assertIn('url=/"', content)

    def test_relative_next_is_honored(self):
        # Sanity check that the validation doesn't block legitimate redirects
        content = self.get_next('/myesp/profile')
        self.assertIn('url=/myesp/profile"', content)

    def test_markup_in_relative_next_is_escaped(self):
        # A relative path passes the host/scheme check, so the escaping in
        # HttpMetaRedirect is what stops this one
        content = self.get_next('/myesp/profile"><script>alert("XSS")</script>')
        self.assertNotIn('<script>', content)
        self.assertIn('&lt;script&gt;', content)


class SignoutRedirectTest(CacheFlushTestCase):
    """ ?redirect= handling on the way out. """

    def setUp(self):
        super().setUp()
        self.signout_url = reverse('signout')

    def test_external_redirect_is_ignored(self):
        response = self.client.get(self.signout_url, {'redirect': EXTERNAL_URL})

        # Falls through to the goodbye page instead of redirecting off-site
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/logged_out.html')

    def test_protocol_relative_redirect_is_ignored(self):
        response = self.client.get(self.signout_url,
                                   {'redirect': '//evil-phishing-site.example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/logged_out.html')

    def test_relative_redirect_is_honored(self):
        response = self.client.get(self.signout_url,
                                   {'redirect': '/myesp/profile'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/myesp/profile')
