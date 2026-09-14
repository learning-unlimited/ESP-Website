from django.test import TestCase
from esp.users.models import K12School, ContactInfo, ESPUser, StudentInfo, RegistrationProfile
from esp.program.modules.handlers.commmodule import _get_school_context_dict
from esp.users.controllers.usersearch import UserSearchController


class SchoolCommTest(TestCase):
    def setUp(self):
        # Separate user for the school contact (not the enrolled student)
        self.contact_user = ESPUser.objects.create(
            username="school_contact",
            first_name="John",
            last_name="Doe",
            email="johndoe@school.edu"
        )
        self.contact = ContactInfo.objects.create(
            user=self.contact_user,
            first_name="John",
            last_name="Doe",
            e_mail="johndoe@school.edu"
        )
        self.school = K12School.objects.create(
            name="Lincoln High School",
            contact=self.contact,
            contact_title="Principal",
            city="Cambridge",
            state="MA"
        )
        # Enrolled student — a different user from the school contact
        self.student_user = ESPUser.objects.create(
            username="student_lincoln",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com"
        )
        self.student_info = StudentInfo.objects.create(
            user=self.student_user,
            k12school=self.school,
            graduation_year=2026
        )
        # Create a RegistrationProfile so _get_school_context_dict finds the school
        # via the RegistrationProfile.student_info path
        self.profile = RegistrationProfile.objects.create(
            user=self.student_user,
            student_info=self.student_info,
            most_recent_profile=True
        )

    def test_k12school_helpers(self):
        self.assertEqual(self.school.get_contact_email(), "johndoe@school.edu")
        self.assertEqual(self.school.get_contact_name(), "John Doe")
        self.assertEqual(self.school.get_contact_titleandlastname(), "Principal Doe")

    def test_school_context_dict_via_registration_profile(self):
        """_get_school_context_dict should find the school via RegistrationProfile.student_info"""
        ctx = _get_school_context_dict(self.student_user, None)
        self.assertEqual(ctx['name'], "Lincoln High School")
        self.assertEqual(ctx['contact_titleandlastname'], "Principal Doe")
        self.assertIn("Alice Smith", ctx['roster'])

    def test_school_context_dict_via_contact_user(self):
        """_get_school_context_dict should find the school via K12School.contact__user fallback"""
        ctx = _get_school_context_dict(self.contact_user, None)
        self.assertEqual(ctx['name'], "Lincoln High School")

    def test_school_context_dict_no_school_returns_empty(self):
        """_get_school_context_dict returns empty dict when user has no associated school"""
        other_user = ESPUser.objects.create(
            username="no_school_user",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com"
        )
        ctx = _get_school_context_dict(other_user, None)
        self.assertEqual(ctx, {})

    def test_get_student_roster_excludes_null_users(self):
        """get_student_roster should not include entries with null users"""
        students = self.school.get_student_roster()
        self.assertNotIn(None, students)
        self.assertIn(self.student_user, students)

    def test_usersearch_school_criteria(self):
        usc = UserSearchController()
        q_result = usc.query_from_criteria("any", {"school": "Lincoln"})
        users = list(ESPUser.objects.filter(q_result))
        self.assertIn(self.student_user, users)
