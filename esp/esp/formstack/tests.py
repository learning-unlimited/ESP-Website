from __future__ import absolute_import

from unittest.mock import patch

from django.test import TestCase, override_settings


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
