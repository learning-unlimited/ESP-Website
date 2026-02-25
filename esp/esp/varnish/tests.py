"""
Tests for esp.varnish.varnish
Source: esp/esp/varnish/varnish.py

Tests Varnish cache purge utilities: get_varnish_host, purge_page, purge_all.
"""
from unittest.mock import patch, MagicMock

from django.test import override_settings

from esp.varnish.varnish import get_varnish_host, purge_all, purge_page
from esp.tests.util import CacheFlushTestCase as TestCase


class GetVarnishHostTest(TestCase):
    @override_settings(VARNISH_HOST='localhost', VARNISH_PORT=6081)
    def test_returns_host_when_configured(self):
        result = get_varnish_host()
        self.assertEqual(result, 'localhost:6081')

    def test_returns_none_when_not_configured(self):
        # Default settings don't have VARNISH_HOST
        from django.conf import settings
        if hasattr(settings, 'VARNISH_HOST'):
            self.skipTest('VARNISH_HOST is set in test settings')
        result = get_varnish_host()
        self.assertIsNone(result)


class PurgePageTest(TestCase):
    def test_returns_none_when_no_varnish(self):
        """If no varnish host is configured, purge_page should return None."""
        from django.conf import settings
        if hasattr(settings, 'VARNISH_HOST'):
            self.skipTest('VARNISH_HOST is set in test settings')
        result = purge_page('/some/url/')
        self.assertIsNone(result)

    @patch('esp.varnish.varnish.http.client.HTTPConnection')
    def test_sends_purge_request(self, MockHTTPConnection):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = 'Purged'
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConnection.return_value = mock_conn

        result = purge_page('/test/', host='localhost:6081')
        self.assertEqual(result, (200, 'Purged'))
        mock_conn.request.assert_called_once()
        args = mock_conn.request.call_args[0]
        self.assertEqual(args[0], 'PURGE')
        self.assertEqual(args[1], '/test/')


class PurgeAllTest(TestCase):
    def test_returns_none_when_no_varnish(self):
        from django.conf import settings
        if hasattr(settings, 'VARNISH_HOST'):
            self.skipTest('VARNISH_HOST is set in test settings')
        result = purge_all()
        self.assertIsNone(result)

    @patch('esp.varnish.varnish.http.client.HTTPConnection')
    def test_sends_ban_request(self, MockHTTPConnection):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = 'Banned'
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConnection.return_value = mock_conn

        result = purge_all(host='localhost:6081')
        self.assertEqual(result, (200, 'Banned'))
        mock_conn.request.assert_called_once()
        args = mock_conn.request.call_args[0]
        self.assertEqual(args[0], 'BAN')
        self.assertEqual(args[1], '/')
