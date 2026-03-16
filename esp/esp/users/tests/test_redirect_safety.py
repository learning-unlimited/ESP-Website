from django.test import RequestFactory, override_settings
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.views import _safe_redirect_target

@override_settings(ALLOWED_HOSTS=['example.com'])
class RedirectSafetyTests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_safe_redirect_target_valid(self):
        request = self.factory.get('/', HTTP_HOST='example.com')
        self.assertEqual(_safe_redirect_target(request, '/foo/bar'), '/foo/bar')
        self.assertEqual(_safe_redirect_target(request, 'http://example.com/foo'), 'http://example.com/foo')

    def test_safe_redirect_target_invalid(self):
        request = self.factory.get('/', HTTP_HOST='example.com')
        self.assertEqual(_safe_redirect_target(request, 'http://malicious.com/'), '')
        self.assertEqual(_safe_redirect_target(request, '//malicious.com/'), '')
        self.assertEqual(_safe_redirect_target(request, 'javascript:alert(1)'), '')
        self.assertEqual(_safe_redirect_target(request, 'https://malicious.com'), '')

    def test_safe_redirect_target_https(self):
        request = self.factory.get('/', HTTP_HOST='example.com', secure=True)
        self.assertEqual(_safe_redirect_target(request, 'https://example.com/foo'), 'https://example.com/foo')
