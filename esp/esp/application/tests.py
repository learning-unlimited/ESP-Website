"""
Tests for esp.application.models
Source: esp/application/models.py

Tests StudentProgramApp and StudentClassApp models.
"""

from django.contrib.auth.models import Group

from esp.application.models import StudentClassApp, StudentProgramApp
from esp.program.models import Program
from esp.program.models.class_ import ClassCategories, ClassSubject
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in [
        "Student",
        "Teacher",
        "Educator",
        "Guardian",
        "Volunteer",
        "Administrator",
    ]:
        Group.objects.get_or_create(name=name)


class StudentProgramAppTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

        self.program = Program.objects.create(
            grade_min=7,
            grade_max=12,
        )

        self.student = ESPUser.objects.create_user(
            username="appstudent",
            password="password",
        )

        self.app = StudentProgramApp.objects.create(
            user=self.student,
            program=self.program,
        )

    def test_str(self):
        self.assertIn("appstudent", str(self.app))

    def test_default_status_unreviewed(self):
        self.assertEqual(
            self.app.admin_status,
            StudentProgramApp.UNREVIEWED,
        )

    def test_choices_empty(self):
        self.assertEqual(self.app.choices(), {})

    def test_admitted_to_class_none(self):
        self.assertIsNone(self.app.admitted_to_class())

    def test_waitlisted_to_class_empty(self):
        self.assertEqual(self.app.waitlisted_to_class(), [])


class StudentClassAppTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

        self.program = Program.objects.create(
            grade_min=7,
            grade_max=12,
        )

        self.student = ESPUser.objects.create_user(
            username="classstudent",
            password="password",
        )

        self.teacher = ESPUser.objects.create_user(
            username="classteacher",
            password="password",
        )

        self.category = ClassCategories.objects.create(
            category="Test Category",
            symbol="T",
            seq=0,
        )

        self.subject = ClassSubject.objects.create(
            parent_program=self.program,
            category=self.category,
            grade_min=7,
            grade_max=12,
        )

        self.program_app = StudentProgramApp.objects.create(
            user=self.student,
            program=self.program,
        )

        self.class_app = StudentClassApp.objects.create(
            app=self.program_app,
            subject=self.subject,
            student_preference=1,
        )

    def test_str(self):
        self.assertIsNotNone(str(self.class_app))

    def test_default_status(self):
        self.assertEqual(
            self.class_app.admission_status,
            StudentClassApp.UNASSIGNED,
        )

    def test_admit(self):
        self.class_app.admit()
        self.class_app.refresh_from_db()

        self.assertEqual(
            self.class_app.admission_status,
            StudentClassApp.ADMITTED,
        )

    def test_unadmit(self):
        self.class_app.admit()
        self.class_app.unadmit()
        self.class_app.refresh_from_db()

        self.assertEqual(
            self.class_app.admission_status,
            StudentClassApp.UNASSIGNED,
        )

    def test_waitlist(self):
        self.class_app.waitlist()
        self.class_app.refresh_from_db()

        self.assertEqual(
            self.class_app.admission_status,
            StudentClassApp.WAITLIST,
        )

    def test_admit_idempotency(self):
        self.class_app.admit()
        self.class_app.refresh_from_db()
        first_status = self.class_app.admission_status

        self.class_app.admit()
        self.class_app.refresh_from_db()
        second_status = self.class_app.admission_status

        self.assertEqual(first_status, second_status)