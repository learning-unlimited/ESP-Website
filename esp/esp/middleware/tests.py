"""
Tests for esp/middleware/fixiemiddleware.py
"""

from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from esp.middleware.fixiemiddleware import FixIEMiddleware


class FixIEMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = FixIEMiddleware()

    def test_ie_user_agent_does_not_crash_for_default_html(self):
        # Default HttpResponse has Content-Type 'text/html; charset=utf-8' by default
        request = self.factory.get('/', HTTP_USER_AGENT='Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1)')
        response = HttpResponse("ok")

        # Check that process_response does not crash and returns the original response unmodified
        new_response = self.middleware.process_response(request, response)
        
        self.assertEqual(new_response.status_code, 200)
        self.assertEqual(new_response.content, b"ok")

    def test_ie_user_agent_strips_vary_for_unsafe_content_type(self):
        # Unsafe content type
        request = self.factory.get('/', HTTP_USER_AGENT='Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1)')
        response = HttpResponse("ok, json", content_type='application/json; charset=utf-8')
        response['Vary'] = 'User-Agent'

        # Check that it strips Vary and adds Pragma & Cache-Control
        new_response = self.middleware.process_response(request, response)
        
        self.assertNotIn('Vary', new_response)
        self.assertEqual(new_response['Pragma'], 'no-cache')
        self.assertEqual(new_response['Cache-Control'], 'no-cache, must-revalidate')
