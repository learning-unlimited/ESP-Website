from django.test import SimpleTestCase

from esp.formstack.api import APIError


class APIErrorTests(SimpleTestCase):
    def test_str_includes_message(self):
        self.assertEqual(str(APIError('Invalid API key')), 'Formstack API error: Invalid API key')

    def test_str_without_args(self):
        self.assertEqual(str(APIError()), 'Formstack API error: ')
