"""
Tests for esp.formstack.objects
Source: esp/esp/formstack/objects.py

Tests FormstackForm and FormstackSubmission objects.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from esp.formstack.api import APIError
from esp.formstack.objects import FormstackForm, FormstackSubmission
from esp.tests.util import CacheFlushTestCase as TestCase


class FormstackFormTest(TestCase):
    def test_init(self):
        form = FormstackForm(12345)
        self.assertEqual(form.id, 12345)
        self.assertIsNone(form.name)
        self.assertIsNone(form.formstack)

    def test_init_with_formstack(self):
        mock_fs = MagicMock()
        form = FormstackForm(99, formstack=mock_fs)
        self.assertEqual(form.formstack, mock_fs)

    def test_str(self):
        form = FormstackForm(42)
        self.assertEqual(str(form), '42')

    def test_repr(self):
        form = FormstackForm(42)
        self.assertEqual(repr(form), '<FormstackForm: 42>')


class FormstackSubmissionTest(TestCase):
    def test_init(self):
        sub = FormstackSubmission(100)
        self.assertEqual(sub.id, 100)
        self.assertIsNone(sub.formstack)

    def test_str(self):
        sub = FormstackSubmission(200)
        self.assertEqual(str(sub), '200')

    def test_repr(self):
        sub = FormstackSubmission(200)
        self.assertEqual(repr(sub), '<FormstackSubmission: 200>')


class FormstackMutableDefaultTests(TestCase):
    def test_form_default_args_are_not_shared(self):
        from esp.formstack.api import Formstack
        fs = Formstack('key')
        with patch.object(fs, '_Formstack__request', return_value={}) as mock_req:
            fs.form(1)
            fs.form(2)
        first_args = mock_req.call_args_list[0][0][1]
        second_args = mock_req.call_args_list[1][0][1]
        self.assertEqual(first_args['id'], 1)
        self.assertEqual(second_args['id'], 2)
        self.assertIsNot(first_args, second_args)


class APIErrorTests(SimpleTestCase):
    def test_str_includes_message(self):
        self.assertEqual(str(APIError('Invalid API key')), 'Formstack API error: Invalid API key')

    def test_str_without_args(self):
        self.assertEqual(str(APIError()), 'Formstack API error: ')
