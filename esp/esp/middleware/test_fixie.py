import unittest
from django.test import RequestFactory
from esp.esp.middleware.fixiemiddleware import FixIEMiddleware


class DummyResponse(dict):
    """
    Simulates legacy Django HttpResponse
    with .mimetype + headers support
    """
    def __init__(self, mimetype):
        super().__init__()
        self.mimetype = mimetype


class FixIEMiddlewareTests(unittest.TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = FixIEMiddleware()

    # 1️⃣ Non-IE browser → unchanged
    def test_non_ie_request(self):
        request = self.factory.get('/')
        request.META['User-Agent'] = 'Chrome'

        response = DummyResponse('application/json')

        processed = self.middleware.process_response(request, response)

        self.assertEqual(processed, response)

    # 2️⃣ IE + SAFE mimetype → unchanged
    def test_ie_safe_mimetype(self):
        request = self.factory.get('/')
        request.META['User-Agent'] = 'MSIE'

        response = DummyResponse('text/html')

        processed = self.middleware.process_response(request, response)

        self.assertEqual(processed, response)

    # 3️⃣ IE + UNSAFE mimetype → headers modified
    def test_ie_unsafe_mimetype_modifies_headers(self):
        request = self.factory.get('/')
        request.META['User-Agent'] = 'MSIE'

        response = DummyResponse('application/json')
        response['Vary'] = 'Cookie'

        processed = self.middleware.process_response(request, response)

        self.assertNotIn('Vary', processed)
        self.assertEqual(processed['Pragma'], 'no-cache')
        self.assertEqual(
            processed['Cache-Control'],
            'no-cache, must-revalidate'
        )

    # 4️⃣ Missing User-Agent → unchanged
    def test_missing_user_agent(self):
        request = self.factory.get('/')

        response = DummyResponse('application/json')

        processed = self.middleware.process_response(request, response)

        self.assertEqual(processed, response)

    # 5️⃣ IE + no Vary header → handled safely
    def test_ie_no_vary_header(self):
        request = self.factory.get('/')
        request.META['User-Agent'] = 'MSIE'

        response = DummyResponse('application/json')

        processed = self.middleware.process_response(request, response)

        self.assertEqual(processed, response)