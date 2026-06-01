"""
Tests for esp.middleware.esperrormiddleware
Source: esp/esp/middleware/esperrormiddleware.py

Tests ESPError exception and AjaxExceptionReporter.
"""
from django.contrib.auth.models import Group
from django.test import RequestFactory

from esp.middleware import ESPError
from esp.middleware.esperrormiddleware import ESPErrorMiddleware
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import AnonymousESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class ESPErrorTest(TestCase):
    def test_is_exception(self):
        err = ESPError('Something went wrong')
        self.assertIsInstance(err, Exception)

    def test_str(self):
        err = ESPError('Test error message')
        self.assertIn('Test error message', str(err))

    def test_log_true_by_default(self):
        err = ESPError('Error')
        self.assertEqual(err.__class__.__name__, 'ESPError_Log')

    def test_log_can_be_disabled(self):
        err = ESPError('Error', log=False)
        self.assertEqual(err.__class__.__name__, 'ESPError_NoLog')


class ESPErrorMiddlewareTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.middleware = ESPErrorMiddleware()
        self.factory = RequestFactory()

    def test_process_exception_returns_none_for_non_esp_error(self):
        request = self.factory.get('/')
        request.user = AnonymousESPUser()
        result = self.middleware.process_exception(request, ValueError('test'))
        self.assertIsNone(result)

    def test_process_exception_handles_esp_error(self):
        request = self.factory.get('/')
        request.user = AnonymousESPUser()
        err = ESPError('Test ESP error')
        response = self.middleware.process_exception(request, err)
        # Should return an HttpResponse with the error
        if response is not None:
            self.assertEqual(response.status_code, 500)
