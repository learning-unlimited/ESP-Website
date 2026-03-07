"""
Tests for esp.formstack
"""
from __future__ import absolute_import

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from esp.formstack.objects import FormstackForm, FormstackSubmission
from esp.tests.util import CacheFlushTestCase


class FormstackWebhookViewTest(TestCase):
    @override_settings(FORMSTACK_HANDSHAKE_KEY='shared-secret')
    def test_valid_webhook_sends_signal(self):
        payload = {
            'FormID': '123',
            'UniqueID': 'abc',
            'HandshakeKey': 'shared-secret',
            'student_name': 'Test Student',
        }
        with patch('esp.formstack.views.formstack_post_signal.send') as mock_send:
            response = self.client.post('/formstack_webhook/', payload)

        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once_with(
            sender=None,
            form_id='123',
            submission_id='abc',
            fields={'student_name': 'Test Student'},
        )

    @override_settings(FORMSTACK_HANDSHAKE_KEY='shared-secret')
    def test_invalid_handshake_is_forbidden(self):
        payload = {
            'FormID': '123',
            'UniqueID': 'abc',
            'HandshakeKey': 'wrong-secret',
        }
        with patch('esp.formstack.views.formstack_post_signal.send') as mock_send:
            response = self.client.post('/formstack_webhook/', payload)

        self.assertEqual(response.status_code, 403)
        mock_send.assert_not_called()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='shared-secret')
    def test_missing_handshake_key_is_forbidden(self):
        payload = {
            'FormID': '123',
            'UniqueID': 'abc',
        }
        with patch('esp.formstack.views.formstack_post_signal.send') as mock_send:
            response = self.client.post('/formstack_webhook/', payload)

        self.assertEqual(response.status_code, 403)
        mock_send.assert_not_called()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='shared-secret')
    def test_missing_required_fields_is_bad_request(self):
        payload = {
            'HandshakeKey': 'shared-secret',
        }
        with patch('esp.formstack.views.formstack_post_signal.send') as mock_send:
            response = self.client.post('/formstack_webhook/', payload)

        self.assertEqual(response.status_code, 400)
        mock_send.assert_not_called()

    @override_settings(FORMSTACK_HANDSHAKE_KEY=None)
    def test_unconfigured_handshake_is_forbidden(self):
        payload = {
            'FormID': '123',
            'UniqueID': 'abc',
            'HandshakeKey': 'anything',
        }
        with patch('esp.formstack.views.formstack_post_signal.send') as mock_send:
            response = self.client.post('/formstack_webhook/', payload)

        self.assertEqual(response.status_code, 403)
        mock_send.assert_not_called()


class FormstackFormTest(CacheFlushTestCase):
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


class FormstackSubmissionTest(CacheFlushTestCase):
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
