"""
Tests for esp.formstack.objects and esp.formstack.views.
Source: esp/esp/formstack/objects.py, esp/esp/formstack/views.py
"""
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, override_settings

from esp.formstack.objects import FormstackForm, FormstackSubmission
from esp.formstack.views import formstack_webhook
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
    """Tests for the handshake key verification in formstack_webhook."""

    def setUp(self):
        self.factory = RequestFactory()
        self.post_data = {
            'FormID': '123',
            'UniqueID': 'abc-456',
        }

    def _make_request(self, extra_data=None):
        data = dict(self.post_data)
        if extra_data:
            data.update(extra_data)
        return self.factory.post('/formstack/webhook/', data=data)

    @override_settings(FORMSTACK_HANDSHAKE_KEY=None)
    @patch('esp.formstack.views.formstack_post_signal')
    def test_no_handshake_key_configured_allows_any_request(self, mock_signal):
        """When FORMSTACK_HANDSHAKE_KEY is None, all requests are accepted."""
        request = self._make_request({'HandshakeKey': 'anything'})
        response = formstack_webhook(request)
        self.assertEqual(response.status_code, 200)
        mock_signal.send.assert_called_once()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='correct-secret')
    @patch('esp.formstack.views.formstack_post_signal')
    def test_valid_handshake_key_returns_200(self, mock_signal):
        """A request with the correct handshake key is accepted."""
        request = self._make_request({'HandshakeKey': 'correct-secret'})
        response = formstack_webhook(request)
        self.assertEqual(response.status_code, 200)
        mock_signal.send.assert_called_once()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='correct-secret')
    @patch('esp.formstack.views.formstack_post_signal')
    def test_invalid_handshake_key_returns_403(self, mock_signal):
        """A request with a wrong handshake key is rejected with HTTP 403."""
        request = self._make_request({'HandshakeKey': 'wrong-secret'})
        response = formstack_webhook(request)
        self.assertEqual(response.status_code, 403)
        mock_signal.send.assert_not_called()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='correct-secret')
    @patch('esp.formstack.views.formstack_post_signal')
    def test_missing_handshake_key_returns_403(self, mock_signal):
        """A request with no HandshakeKey field is rejected when a key is configured."""
        request = self._make_request()  # no HandshakeKey in POST data
        response = formstack_webhook(request)
        self.assertEqual(response.status_code, 403)
        mock_signal.send.assert_not_called()

    @override_settings(FORMSTACK_HANDSHAKE_KEY='')
    @patch('esp.formstack.views.formstack_post_signal')
    def test_empty_string_key_still_enforces_verification(self, mock_signal):
        """An empty-string key should still enforce verification, not silently skip it."""
        request = self._make_request({'HandshakeKey': 'some-key'})
        response = formstack_webhook(request)
        self.assertEqual(response.status_code, 403)
        mock_signal.send.assert_not_called()

