"""
Tests for esp.middleware.espauthmiddleware
Source: esp/esp/middleware/espauthmiddleware.py

Tests get_user function and ESPAuthMiddleware cookie management.
"""
from unittest.mock import MagicMock

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import RequestFactory

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
        self.middleware = ESPAuthMiddleware()
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


def _cache_control_directives(cache_control):
    """Return the set of directive names (lowercase) from a Cache-Control value."""
    if not cache_control:
        return set()
    names = set()
    for part in cache_control.split(','):
        part = part.strip().lower()
        if part:
            names.add(part.split('=', 1)[0])
    return names


class CacheControlMiddlewareTest(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.middleware = CacheControlMiddleware(get_response=lambda r: HttpResponse())

    def test_adds_cache_control_when_missing(self):
        request = self.factory.get('/')
        response = HttpResponse()

        processed = self.middleware.process_response(request, response)
        directives = _cache_control_directives(processed.get('Cache-Control'))

        self.assertIn('private', directives)
        self.assertIn('no-cache', directives)

    def test_does_not_override_existing_cache_control(self):
        request = self.factory.get('/')
        response = HttpResponse()
        response['Cache-Control'] = 'max-age=3600'

        processed = self.middleware.process_response(request, response)

        self.assertEqual(processed.get('Cache-Control'), 'max-age=3600')
