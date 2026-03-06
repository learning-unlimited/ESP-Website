"""
Tests for EmailList population (Issue #3013)
"""

from django.test import TestCase
from esp.dbmail.models import EmailList


class EmailListPopulationTestCase(TestCase):
    """
    Test that default EmailList entries are created properly.
    """

    def test_default_emaillists_exist(self):
        """
        Test that the default EmailList entries exist after migration.
        """
        # Check that we have email lists
        email_lists = EmailList.objects.all()
        self.assertGreater(
            email_lists.count(), 0,
            "No EmailList entries found. Default email lists should be created by migration."
        )

    def test_section_list_handler_exists(self):
        """
        Test that SectionList handler is configured.
        """
        section_lists = EmailList.objects.filter(handler='SectionList')
        self.assertGreater(
            section_lists.count(), 0,
            "SectionList handler not found in EmailList entries"
        )

        # Verify the regex pattern
        section_list = section_lists.first()
        self.assertIn('students', section_list.regex)
        self.assertIn('teachers', section_list.regex)

    def test_class_list_handler_exists(self):
        """
        Test that ClassList handler is configured.
        """
        class_lists = EmailList.objects.filter(handler='ClassList')
        self.assertGreater(
            class_lists.count(), 0,
            "ClassList handler not found in EmailList entries"
        )

    def test_plain_list_handler_exists(self):
        """
        Test that PlainList handler is configured.
        """
        plain_lists = EmailList.objects.filter(handler='PlainList')
        self.assertGreater(
            plain_lists.count(), 0,
            "PlainList handler not found in EmailList entries"
        )

    def test_user_email_handler_exists(self):
        """
        Test that UserEmail handler is configured.
        """
        user_email_lists = EmailList.objects.filter(handler='UserEmail')
        self.assertGreater(
            user_email_lists.count(), 0,
            "UserEmail handler not found in EmailList entries"
        )

    def test_email_lists_have_proper_sequence(self):
        """
        Test that email lists are ordered by sequence number.
        """
        email_lists = list(EmailList.objects.all().order_by('seq'))

        # Verify we have at least 4 default lists
        self.assertGreaterEqual(len(email_lists), 4)

        # Verify they are in ascending order
        for i in range(len(email_lists) - 1):
            self.assertLessEqual(
                email_lists[i].seq, email_lists[i + 1].seq,
                "EmailList entries should be ordered by sequence number"
            )
