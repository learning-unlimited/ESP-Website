"""
Tests for esp.middleware.esperrormiddleware
Source: esp/esp/middleware/esperrormiddleware.py

Tests ESPError exception and AjaxExceptionReporter.
"""
import json

from django.contrib.auth.models import Group
from django.core.exceptions import BadRequest, PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.test import RequestFactory

from esp.middleware import ESPError
from esp.middleware.esperrormiddleware import ESPError_Log, ESPErrorMiddleware, Http403
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
        self.middleware = ESPErrorMiddleware(get_response=lambda request: None)
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

    def test_process_exception_ajax_request_returns_json_for_esp_error(self):
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        err = ESPError('Test AJAX error', log=False)
        response = self.middleware.process_exception(request, err)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        content_type = response.headers.get('Content-Type') if hasattr(response, 'headers') else response.get('Content-Type')
        self.assertEqual(content_type, 'application/json')
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 500)
        self.assertEqual(data['error'], 'Test AJAX error')

    def test_process_exception_ajax_request_returns_json_for_internal_error(self):
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        err = ESPError('Sensitive internal error', log=True)
        response = self.middleware.process_exception(request, err)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 500)
        self.assertEqual(data['error'], self.middleware._ERROR_MESSAGES['ESPError_Log'][1])

    def test_process_exception_ajax_request_returns_json_for_http404(self):
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, Http404('Resource not found'))
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 404)
        content_type = response.headers.get('Content-Type') if hasattr(response, 'headers') else response.get('Content-Type')
        self.assertEqual(content_type, 'application/json')
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 404)
        self.assertEqual(data['error'], 'Resource not found')

    def test_process_exception_ajax_request_returns_json_for_http403(self):
        request = self.factory.post('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, Http403())
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)
        content_type = response.headers.get('Content-Type') if hasattr(response, 'headers') else response.get('Content-Type')
        self.assertEqual(content_type, 'application/json')
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 403)
        self.assertIn('permission', data['error'])

    def test_process_exception_ajax_request_unhandled_exception(self):
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, ValueError('db crash'))
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 500)
        self.assertEqual(data['error'], self.middleware._ERROR_MESSAGES['ESPError_Log'][1])

    def test_process_exception_ajax_request_accept_header(self):
        request = self.factory.get('/', HTTP_ACCEPT='application/json')
        request.user = AnonymousESPUser()
        err = ESPError('Test JSON Accept error', log=False)
        response = self.middleware.process_exception(request, err)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['error'], 'Test JSON Accept error')

    def test_process_exception_ajax_legacy_class_returns_friendly_description(self):
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, ESPError_Log)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 500)
        self.assertIn('website encountered an error', data['error'])

    def test_process_exception_ajax_request_returns_json_for_permission_denied(self):
        request = self.factory.post('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, PermissionDenied('Custom access denied'))
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 403)
        self.assertEqual(data['error'], 'Custom access denied')

    def test_process_exception_ajax_request_returns_json_for_bad_request(self):
        request = self.factory.post('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, BadRequest('Malformed JSON data'))
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 400)
        self.assertEqual(data['error'], 'Malformed JSON data')

    def test_process_exception_ajax_request_returns_json_for_suspicious_operation(self):
        request = self.factory.post('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousESPUser()
        response = self.middleware.process_exception(request, SuspiciousOperation('Invalid host'))
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 400)
        self.assertEqual(data['error'], 'Invalid host')
