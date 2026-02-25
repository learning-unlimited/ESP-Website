"""
Tests for esp.program.controllers.testingutils.TestDataCleanupController.

These tests verify:
1. That wipe_test_data deletes the expected objects for (program, user).
2. That it does NOT delete objects belonging to other users in the same program.
3. That it does NOT delete objects from other programs.
"""
from __future__ import absolute_import

from esp.program.controllers.testingutils import TestDataCleanupController
from esp.program.models import (
    RegistrationType, StudentRegistration, StudentSubjectInterest,
    FinancialAidRequest, RegistrationProfile,
)
from esp.program.models.class_ import ClassSubject
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.users.models import ESPUser, ContactInfo, Record, RecordType


class TestDataCleanupTest(TestCase):
    """Tests for TestDataCleanupController using a minimal hand-built fixture.

    We build only what we need so the test stays fast and self-contained.
    """

    def setUp(self):
        user_role_setup()

        # Two programs
        from esp.program.models import ClassCategories, ProgramModule
        from esp.program.forms import ProgramCreationForm
        from esp.program.setup import prepare_program, commit_program
        import unicodedata
        import re

        def make_program(slug):
            categories = []
            cat, _ = ClassCategories.objects.get_or_create(
                category='Category A', symbol='A')
            categories.append(cat)

            admin, _ = ESPUser.objects.get_or_create(
                username='admin_%s' % slug,
                defaults={'first_name': 'Admin', 'last_name': slug,
                          'email': 'admin_%s@test.example' % slug})
            admin.set_password('password')
            admin.save()
            admin.makeRole('Administrator')

            prog_form_values = {
                'term': '2222_%s' % slug,
                'term_friendly': 'Summer 2222 %s' % slug,
                'grade_min': '7',
                'grade_max': '12',
                'director_email': 'info@test.learningu.org',
                'program_size_max': '3000',
                'program_type': 'TestProg',
                'program_modules': ProgramModule.objects.all(),
                'class_categories': [cat.id for cat in categories],
                'admins': [admin.id],
                'teacher_reg_start': '2000-01-01 00:00:00',
                'teacher_reg_end': '3001-01-01 00:00:00',
                'student_reg_start': '2000-01-01 00:00:00',
                'student_reg_end': '3001-01-01 00:00:00',
                'base_cost': '0',
                'sibling_discount': '0',
            }
            pcf = ProgramCreationForm(prog_form_values)
            if not pcf.is_valid():
                raise Exception("ProgramCreationForm errors: %s" % pcf.errors)
            temp_prog = pcf.save(commit=False)
            perms, modules = prepare_program(temp_prog, pcf.data)
            new_prog = pcf.save(commit=False)
            ptype_slug = re.sub(
                r'[-\s]+', '_',
                re.sub(r'[^\w\s-]', '', unicodedata.normalize(
                    'NFKD', pcf.cleaned_data['program_type'])).strip())
            new_prog.url = ptype_slug + '/' + pcf.cleaned_data['term']
            new_prog.name = (pcf.cleaned_data['program_type'] + ' ' +
                             pcf.cleaned_data['term_friendly'])
            new_prog.save()
            pcf.save_m2m()
            commit_program(new_prog, perms,
                           pcf.cleaned_data['base_cost'],
                           pcf.cleaned_data['sibling_discount'])
            from django.contrib.auth.models import Group
            Group.objects.get_or_create(name='Teacher')
            Group.objects.get_or_create(name='Student')
            return new_prog

        self.prog = make_program('alpha')
        self.other_prog = make_program('beta')

        # Users
        def make_user(username, role):
            u, _ = ESPUser.objects.get_or_create(
                username=username,
                defaults={'first_name': username, 'last_name': 'Test',
                          'email': '%s@test.example' % username})
            u.set_password('password')
            u.save()
            u.makeRole(role)
            return u

        self.student = make_user('wipe_student_a', 'Student')
        self.other_student = make_user('wipe_student_b', 'Student')
        self.teacher = make_user('wipe_teacher_a', 'Teacher')

        # A class section in self.prog
        cat, _ = ClassSubject.objects.model._meta.get_field(
            'category').related_model.objects.get_or_create(
                category='Category A', symbol='A')
        self.cls = ClassSubject.objects.create(
            title='Wipe Test Class',
            category=cat,
            grade_min=7, grade_max=12,
            parent_program=self.prog,
            class_size_max=30,
        )
        self.cls.makeTeacher(self.teacher)
        self.cls.add_section(duration=1.0)
        self.section = self.cls.get_sections()[0]

        # StudentRegistration for self.student
        enrolled, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', category='student')
        self.sr = StudentRegistration.objects.create(
            user=self.student,
            section=self.section,
            relationship=enrolled,
        )

        # StudentRegistration for self.other_student (must NOT be deleted)
        self.sr_other = StudentRegistration.objects.create(
            user=self.other_student,
            section=self.section,
            relationship=enrolled,
        )

        # StudentSubjectInterest
        self.ssi = StudentSubjectInterest.objects.create(
            user=self.student,
            subject=self.cls,
        )

        # Record
        rec_type, _ = RecordType.objects.get_or_create(name='reg_confirmed')
        self.rec = Record.objects.create(
            user=self.student,
            program=self.prog,
            event=rec_type,
        )

        # FinancialAidRequest
        self.fin = FinancialAidRequest.objects.create(
            user=self.student,
            program=self.prog,
        )

        # RegistrationProfile
        ci, _ = ContactInfo.objects.get_or_create(
            user=self.student,
            first_name=self.student.first_name,
            last_name=self.student.last_name,
            e_mail=self.student.email,
        )
        self.profile = RegistrationProfile.objects.create(
            user=self.student,
            program=self.prog,
            contact_user=ci,
        )

        # --- Object in OTHER program (must NOT be deleted) ---
        self.rec_other_prog = Record.objects.create(
            user=self.student,
            program=self.other_prog,
            event=rec_type,
        )

    # ------------------------------------------------------------------

    def test_wipe_deletes_student_data(self):
        """execute() removes student-side data for the target user+program."""
        ctrl = TestDataCleanupController(self.prog, self.student)
        counts = ctrl.get_counts()
        self.assertGreater(counts['student_registrations'], 0)
        self.assertGreater(counts['records'], 0)

        ctrl.execute()

        self.assertFalse(
            StudentRegistration.objects.filter(id=self.sr.id).exists(),
            'StudentRegistration should be deleted',
        )
        self.assertFalse(
            StudentSubjectInterest.objects.filter(id=self.ssi.id).exists(),
            'StudentSubjectInterest should be deleted',
        )
        self.assertFalse(
            Record.objects.filter(id=self.rec.id).exists(),
            'Record should be deleted',
        )
        self.assertFalse(
            FinancialAidRequest.objects.filter(id=self.fin.id).exists(),
            'FinancialAidRequest should be deleted',
        )
        self.assertFalse(
            RegistrationProfile.objects.filter(id=self.profile.id).exists(),
            'RegistrationProfile should be deleted',
        )

    def test_wipe_does_not_touch_other_user(self):
        """execute() must not delete data that belongs to a different user."""
        ctrl = TestDataCleanupController(self.prog, self.student)
        ctrl.execute()

        self.assertTrue(
            StudentRegistration.objects.filter(id=self.sr_other.id).exists(),
            'Other student registration must be preserved',
        )

    def test_wipe_does_not_touch_other_program(self):
        """execute() must not delete records from a different program."""
        ctrl = TestDataCleanupController(self.prog, self.student)
        ctrl.execute()

        self.assertTrue(
            Record.objects.filter(id=self.rec_other_prog.id).exists(),
            'Record from a different program must be preserved',
        )
