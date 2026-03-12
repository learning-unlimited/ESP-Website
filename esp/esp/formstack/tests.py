"""
Tests for esp.formstack.objects
Source: esp/esp/formstack/objects.py

Tests FormstackForm and FormstackSubmission objects.
"""
from unittest.mock import MagicMock, patch

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


class FormstackWebhookTest(TestCase):
    """Tests for formstack_webhook handshake key verification."""

    def test_webhook_rejects_wrong_handshake_key(self):
        """POST with wrong handshake key should return 403."""
        with self.settings(FORMSTACK_HANDSHAKE_KEY='correct-secret'):
            response = self.client.post('/formstack_webhook', {
                'FormID': '123',
                'UniqueID': '456',
                'HandshakeKey': 'wrong-key',
            })
            self.assertEqual(response.status_code, 403)

    def test_webhook_accepts_correct_handshake_key(self):
        """POST with correct handshake key should succeed."""
        with self.settings(FORMSTACK_HANDSHAKE_KEY='correct-secret'):
            response = self.client.post('/formstack_webhook', {
                'FormID': '123',
                'UniqueID': '456',
                'HandshakeKey': 'correct-secret',
            })
            self.assertEqual(response.status_code, 200)

    def test_webhook_accepts_any_key_when_not_configured(self):
        """When FORMSTACK_HANDSHAKE_KEY is empty, all requests pass."""
        with self.settings(FORMSTACK_HANDSHAKE_KEY=''):
            response = self.client.post('/formstack_webhook', {
                'FormID': '123',
                'UniqueID': '456',
                'HandshakeKey': 'anything',
            })
            self.assertEqual(response.status_code, 200)

    def test_webhook_rejects_get(self):
        """GET requests to the webhook should return 404."""
        response = self.client.get('/formstack_webhook')
        self.assertEqual(response.status_code, 404)


class MedicalsyncapiCsrfTest(TestCase):
    """Tests that medicalsyncapi enforces CSRF protection."""

    def test_medicalsyncapi_rejects_post_without_csrf(self):
        """POST without CSRF token should return 403."""
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post('/medicalsyncapi', {
            'username': 'admin',
            'password': 'password',
            'program': 'Splash 2024',
        })
        self.assertEqual(response.status_code, 403)
