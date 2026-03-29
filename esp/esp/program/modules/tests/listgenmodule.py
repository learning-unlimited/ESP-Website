"""
Tests for List Generator Module
"""

from django.test import TestCase, Client
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import Program
from esp.users.models import ESPUser
from esp.middleware import ESPError


class ListGenModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        # Create admin user for testing
        self.admin = ESPUser.objects.create_user(
            username='testadmin',
            password='password',
            first_name='Test',
            last_name='Admin'
        )
        self.admin.makeAdmin()
        self.client = Client()
        self.assertTrue(self.client.login(username='testadmin', password='password'))

    def test_selectList_old_handles_missing_filter_gracefully(self):
        """
        Test that selectList_old raises a user-friendly ESPError
        when given an invalid/stale filter ID instead of crashing.
        """
        response = self.client.get(
            '/manage/{}/selectList_old'.format(self.program.getUrlBase()),
            {'filterid': '999999999'}
        )
        
        # Should get a 500 response with friendly error message
        self.assertEqual(response.status_code, 500)
        self.assertIn(
            'recipient filter is invalid or expired',
            response.content.decode('UTF-8').lower()
        )
