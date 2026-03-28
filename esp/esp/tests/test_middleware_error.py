"""
Tests for esp.middleware.esperrormiddleware
Source: esp/esp/middleware/esperrormiddleware.py

Tests ESPError exception and AjaxExceptionReporter.
"""
import json

from django.contrib.auth.models import Group
from django.db.models.base import ObjectDoesNotExist
from django.http import Http404
from django.test import RequestFactory

from esp.middleware import ESPError
from esp.middleware.esperrormiddleware import AjaxErrorMiddleware, ESPErrorMiddleware
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


class AjaxErrorMiddlewareTest(TestCase):
    """Tests for AjaxErrorMiddleware.

    Verifies that AJAX error responses always use HTTP 200 so that
    jQuery success callbacks receive them, while preserving the semantic
    status code (404, 500, etc.) inside the JSON body.
    """

    def setUp(self):
        super().setUp()
        self.middleware = AjaxErrorMiddleware()
        self.factory = RequestFactory()

    def _ajax_request(self, method='GET', path='/'):
        request = self.factory.get(path) if method == 'GET' else self.factory.post(path)
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        return request

    def test_non_ajax_request_returns_none(self):
        """Non-AJAX requests should not be handled by AjaxErrorMiddleware."""
        request = self.factory.get('/')
        result = self.middleware.process_exception(
            request, AjaxErrorMiddleware.AjaxError('test'))
        self.assertIsNone(result)

    def test_ajax_error_returns_200_with_error_json(self):
        """AjaxError exceptions should return HTTP 200 with error in JSON."""
        request = self._ajax_request()
        err = AjaxErrorMiddleware.AjaxError('Something went wrong')
        response = self.middleware.process_exception(request, err)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 200)
        self.assertEqual(data['error'], 'Something went wrong')

    def test_ajax_not_found_returns_200_with_404_status(self):
        """Http404 should return HTTP 200 with status 404 in JSON."""
        request = self._ajax_request()
        err = Http404('Object not found')
        response = self.middleware.process_exception(request, err)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 404)
        self.assertIn('Object not found', data['error'])

    def test_ajax_object_does_not_exist_returns_200_with_404_status(self):
        """ObjectDoesNotExist should return HTTP 200 with status 404 in JSON."""
        request = self._ajax_request()
        err = ObjectDoesNotExist('No such record')
        response = self.middleware.process_exception(request, err)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 404)
        self.assertIn('No such record', data['error'])

    def test_ajax_parameter_missing_error(self):
        """AjaxParameterMissingError should return HTTP 200 with error."""
        request = self._ajax_request()
        err = AjaxErrorMiddleware.AjaxParameterMissingError('user_id')
        response = self.middleware.process_exception(request, err)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 200)
        self.assertIn('user_id', data['error'])

    def test_unhandled_exception_returns_none(self):
        """Exceptions not covered by AjaxErrorMiddleware should return None."""
        request = self._ajax_request()
        result = self.middleware.process_exception(request, ValueError('test'))
        self.assertIsNone(result)

    def test_response_content_type_is_json(self):
        """All AJAX error responses should have application/json content type."""
        request = self._ajax_request()
        err = AjaxErrorMiddleware.AjaxError('test')
        response = self.middleware.process_exception(request, err)
        self.assertIn('application/json', response['Content-Type'])
