"""
Tests for esp.middleware.espauthmiddleware and esp.middleware.cache_control
Source: esp/esp/middleware/espauthmiddleware.py, esp/esp/middleware/cache_control.py

Tests get_user function, ESPAuthMiddleware cookie management, and the
default Cache-Control policy applied by CacheControlMiddleware.
"""
from unittest.mock import MagicMock

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import re_path
from django.views.decorators.cache import cache_control

from esp.middleware.cache_control import CacheControlMiddleware
from esp.middleware.espauthmiddleware import ESPAuthMiddleware, get_user
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import AnonymousESPUser, ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class GetUserTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.factory = RequestFactory()

    def test_anonymous_user_returns_anonymous_esp_user(self):
        request = self.factory.get('/')
        request.session = self.client.session
        user = get_user(request)
        self.assertIsInstance(user, AnonymousESPUser)

    def test_caches_user(self):
        request = self.factory.get('/')
        request.session = self.client.session
        user1 = get_user(request)
        user2 = get_user(request)
        self.assertIs(user1, user2)


class ESPAuthMiddlewareProcessResponseTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.middleware = ESPAuthMiddleware(get_response=lambda request: None)
        self.factory = RequestFactory()

    def test_no_set_cookies_flag(self):
        """If response has no_set_cookies=True, should return response unchanged."""
        request = self.factory.get('/')
        request.session = self.client.session
        request._cached_user = AnonymousESPUser()
        response = MagicMock()
        response.no_set_cookies = True
        result = self.middleware.process_response(request, response)
        self.assertEqual(result, response)

    def test_anonymous_user_deletes_cookies(self):
        """For anonymous users, existing user cookies should be deleted."""
        request = self.factory.get('/')
        request.session = self.client.session
        request._cached_user = AnonymousESPUser()
        request.COOKIES = {
            'cur_username': 'old_user',
            'cur_userid': '1',
            'cur_email': 'old@test.com',
        }

        response = HttpResponse()
        result = self.middleware.process_response(request, response)
        self.assertIsNotNone(result)

    def test_authenticated_user_sets_cookies(self):
        """For authenticated users, cookies should be set."""
        user = ESPUser.objects.create_user(
            username='cookieuser',
            password='password',
            email='cookie@test.com',
            first_name='Cookie',
            last_name='User',
        )

        request = self.factory.get('/')
        request.session = self.client.session
        request._cached_user = user
        request.COOKIES = {}
        request.encoding = None

        response = HttpResponse()
        result = self.middleware.process_response(request, response)
        cookie_names = result.cookies.keys()
        self.assertIn('cur_username', cookie_names)
        self.assertIn('cur_userid', cookie_names)
        self.assertIn('cur_email', cookie_names)


def _cache_control_directives(header):
    """Parse a Cache-Control header into a {directive: value} dict."""
    directives = {}
    for part in (header or '').split(','):
        part = part.strip().lower()
        if part:
            name, _, value = part.partition('=')
            directives[name] = value or True
    return directives


class CacheControlMiddlewareTest(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.middleware = CacheControlMiddleware(get_response=lambda request: HttpResponse())

    def _process(self, response):
        return self.middleware.process_response(self.factory.get('/'), response)

    def test_adds_default_policy_when_missing(self):
        response = self._process(HttpResponse())
        self.assertEqual(_cache_control_directives(response.get('Cache-Control')),
                         {'private': True, 'no-cache': True})

    def test_does_not_override_existing_cache_control(self):
        response = HttpResponse()
        response['Cache-Control'] = 'public, max-age=3600'
        self.assertEqual(self._process(response).get('Cache-Control'), 'public, max-age=3600')

    @override_settings(DEFAULT_CACHE_CONTROL={'no_store': True, 'max_age': 0})
    def test_uses_configured_directives(self):
        response = self._process(HttpResponse())
        self.assertEqual(_cache_control_directives(response.get('Cache-Control')),
                         {'no-store': True, 'max-age': '0'})

    @override_settings(DEFAULT_CACHE_CONTROL={})
    def test_can_be_disabled(self):
        self.assertFalse(self._process(HttpResponse()).has_header('Cache-Control'))


# Views and URLs for CacheControlMiddlewareIntegrationTest, which exercises the
# real middleware stack rather than calling process_response() directly.
def _plain_view(request):
    return HttpResponse('plain')


@cache_control(public=True, max_age=180)
def _cached_view(request):
    return HttpResponse('cached')


urlpatterns = [
    re_path(r'^cache-control/plain$', _plain_view),
    re_path(r'^cache-control/cached$', _cached_view),
]


@override_settings(ROOT_URLCONF=__name__)
class CacheControlMiddlewareIntegrationTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_middleware_is_installed(self):
        response = self.client.get('/cache-control/plain')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_cache_control_directives(response.get('Cache-Control')),
                         {'private': True, 'no-cache': True})

    def test_view_policy_is_preserved(self):
        response = self.client.get('/cache-control/cached')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_cache_control_directives(response.get('Cache-Control')),
                         {'public': True, 'max-age': '180'})
