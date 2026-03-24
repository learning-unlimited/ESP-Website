from django.test import TestCase, RequestFactory
from esp.tests.views import javascript_tests

class TestJavascriptTestsView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_javascript_tests_view(self):
        request = self.factory.get('/')
        response = javascript_tests(request)
        self.assertEqual(response.status_code, 200)