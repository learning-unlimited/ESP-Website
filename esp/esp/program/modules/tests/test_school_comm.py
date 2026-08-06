from django.test import TestCase
from esp.users.models import K12School, ContactInfo, ESPUser, StudentInfo
from esp.program.modules.handlers.commmodule import _get_school_context_dict
from esp.users.controllers.usersearch import UserSearchController


class SchoolCommTest(TestCase):
    def setUp(self):
        self.student_user = ESPUser.objects.create(
            username="student_lincoln",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com"
        )
        self.contact = ContactInfo.objects.create(
            user=self.student_user,
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
        self.student_info = StudentInfo.objects.create(
            user=self.student_user,
            k12school=self.school,
            graduation_year=2026
        )

    def test_k12school_helpers(self):
        self.assertEqual(self.school.get_contact_email(), "johndoe@school.edu")
        self.assertEqual(self.school.get_contact_name(), "John Doe")
        self.assertEqual(self.school.get_contact_titleandlastname(), "Principal Doe")

    def test_school_context_dict(self):
        ctx = _get_school_context_dict(self.student_user, None)
        self.assertEqual(ctx['name'], "Lincoln High School")
        self.assertEqual(ctx['contact_titleandlastname'], "Principal Doe")
        self.assertIn("Alice Smith", ctx['roster'])

    def test_usersearch_school_criteria(self):
        usc = UserSearchController()
        q_result = usc.query_from_criteria("any", {"school": "Lincoln"})
        users = list(ESPUser.objects.filter(q_result))
        self.assertIn(self.student_user, users)
