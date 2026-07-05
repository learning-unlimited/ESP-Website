"""
Behavioral tests for AdminReviewApps (esp/program/modules/handlers/adminreviewapps.py).

accept_student() and reject_student() create and expire StudentRegistration
objects with relationship='Accepted'.

Refs: #3780, #3773
"""

from esp.program.models import ClassSubject, StudentRegistration, RegistrationType
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class AdminReviewAppsTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self):
        super().setUp()
        self.student = self.students[0]
        self.cls = ClassSubject.objects.filter(parent_program=self.program).first()
        self.section = self.cls.get_sections()[0]
        self.accepted_rt, _ = RegistrationType.objects.get_or_create(
            name='Accepted', defaults={'category': 'student'}
        )

    def _accept_url(self):
        # accept_student() expects extra=class_id in URL path
        return self.get_module_url('manage', 'accept_student', extra=str(self.cls.id)) + \
               f'?student={self.student.id}'

    def _reject_url(self):
        # reject_student() expects extra=class_id in URL path
        return self.get_module_url('manage', 'reject_student', extra=str(self.cls.id)) + \
               f'?student={self.student.id}'

    def test_accept_student_creates_accepted_registration(self):
        """accept_student() creates a StudentRegistration with relationship='Accepted'."""
        self.login_as('admin')
        self.client.get(self._accept_url())
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.section,
                relationship__name='Accepted',
            ).exists(),
            'accept_student() should create a valid Accepted registration'
        )

    def test_reject_student_expires_accepted_registration(self):
        """reject_student() expires the Accepted registration."""
        # Set up: accept first
        StudentRegistration.objects.get_or_create(
            user=self.student,
            section=self.section,
            relationship=self.accepted_rt,
        )
        self.login_as('admin')
        self.client.get(self._reject_url())
        self.assertEqual(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.section,
                relationship__name='Accepted',
            ).count(),
            0,
            'reject_student() should expire all Accepted registrations'
        )

    def test_student_cannot_accept(self):
        """Non-admin gets notanadmin error page for accept_student."""
        self.login_as('student')
        response = self.client.get(self._accept_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    def test_student_cannot_reject(self):
        """Non-admin gets notanadmin error page for reject_student."""
        self.login_as('student')
        response = self.client.get(self._reject_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')
