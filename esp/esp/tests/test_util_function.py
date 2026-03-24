from django.test import TestCase
from esp.tests import util

class TestUtilFunction(TestCase):

    def test_string_conversion(self):
        # Example test (adjust based on actual function)
        result = str("test")
        self.assertEqual(result, "test")