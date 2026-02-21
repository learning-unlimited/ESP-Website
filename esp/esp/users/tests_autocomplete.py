from __future__ import absolute_import
from django.test import TestCase
from esp.users.models import ESPUser, StudentInfo
from django.contrib.auth.models import Group
from django.db.models import Q

class AutocompleteTest(TestCase):
    def setUp(self):
        # Create groups
        self.student_group, _ = Group.objects.get_or_create(name="Student")

        # Create a program
        from django.apps import apps
        Program = apps.get_model('program', 'Program')
        self.program = Program.objects.create(name="Test Program", url="testprog")
        # Ensure program has some dates so current_schoolyear works
        from esp.cal.models import Event, EventType
        et, _ = EventType.objects.get_or_create(description='Class Time Block')
        Event.objects.create(program=self.program, event_type=et, start='2024-01-01 10:00:00', end='2024-01-01 11:00:00',
                             name="Test Event", short_description="Test", description="Test Event Description")

        # Create some students
        self.s1 = ESPUser.objects.create(username="s1", first_name="Alice", last_name="Alpha")
        self.s1.groups.add(self.student_group)

        self.s2 = ESPUser.objects.create(username="s2", first_name="Bob", last_name="Bravo")
        self.s2.groups.add(self.student_group)

        self.s3 = ESPUser.objects.create(username="s3", first_name="Charlie", last_name="Alpha")
        self.s3.groups.add(self.student_group)

        # Set up student info and profiles for grade filtering
        # Assume school year 2024. Grade 10 -> YOG = 2024 + (12 - 10) = 2026
        # Grade 8 -> YOG = 2024 + (12 - 8) = 2028

        si1 = StudentInfo.objects.create(user=self.s1, graduation_year=2026)
        si2 = StudentInfo.objects.create(user=self.s2, graduation_year=2028)

        RegistrationProfile = apps.get_model('program', 'RegistrationProfile')
        RegistrationProfile.objects.create(user=self.s1, program=self.program, student_info=si1)
        RegistrationProfile.objects.create(user=self.s2, program=self.program, student_info=si2)

    def test_first_name_search(self):
        """Test searching by first name alone."""
        # Searching "Alice" should return s1
        results = ESPUser.ajax_autocomplete("Alice")
        usernames = [r['username'] for r in results]
        self.assertIn("s1", usernames)

        # Searching "Bob" should return s2
        results = ESPUser.ajax_autocomplete("Bob")
        usernames = [r['username'] for r in results]
        self.assertIn("s2", usernames)

    def test_last_name_search(self):
        """Test that last name search still works."""
        results = ESPUser.ajax_autocomplete("Alpha")
        usernames = [r['username'] for r in results]
        self.assertIn("s1", usernames)
        self.assertIn("s3", usernames)

    def test_grade_filter(self):
        """Test filtering by grade."""
        # Grade 10 should return Alice (s1) but not Bob (s2)
        results = ESPUser.ajax_autocomplete("A", grade="10", prog=self.program.id)
        usernames = [r['username'] for r in results]
        self.assertIn("s1", usernames)
        self.assertNotIn("s2", usernames)

        # Grade 8 should return Bob (s2)
        results = ESPUser.ajax_autocomplete("B", grade="8", prog=self.program.id)
        usernames = [r['username'] for r in results]
        self.assertIn("s2", usernames)
        self.assertNotIn("s1", usernames)

    def test_last_name_range_filter(self):
        """Test filtering by last name range."""
        # Range A-G should include Alpha and Bravo
        results = ESPUser.ajax_autocomplete("s", last_name_range="A-G")
        usernames = [r['username'] for r in results]
        self.assertIn("s1", usernames)
        self.assertIn("s2", usernames)

        # Range H-Z should NOT include Alpha or Bravo
        results = ESPUser.ajax_autocomplete("s", last_name_range="H-Z")
        usernames = [r['username'] for r in results]
        self.assertNotIn("s1", usernames)
        self.assertNotIn("s2", usernames)
