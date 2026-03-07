from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from esp.middleware.cache_control import CacheControlMiddleware

class CacheControlMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CacheControlMiddleware(get_response=lambda r: HttpResponse())

    def test_adds_cache_control_when_missing(self):
        request = self.factory.get('/')
        response = HttpResponse()
        
        processed_response = self.middleware.process_response(request, response)

        self.assertEqual(processed_response.get('Cache-Control'), 'private, no-cache')

    def test_does_not_override_existing_cache_control(self):
        request = self.factory.get('/')
        response = HttpResponse()
        response['Cache-Control'] = 'max-age=3600'
        
        processed_response = self.middleware.process_response(request, response)

        self.assertEqual(processed_response.get('Cache-Control'), 'max-age=3600')
