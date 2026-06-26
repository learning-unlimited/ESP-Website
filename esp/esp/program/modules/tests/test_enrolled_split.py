from __future__ import absolute_import

import datetime

from esp.tests.util import CacheFlushTestCase
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import Program, ClassSubject, StudentRegistration, RegistrationType
from esp.cal.models import Event, EventType


class EnrolledSplitViewTest(ProgramFrameworkTest, CacheFlushTestCase):
    """
    Tests that /manage/userview correctly splits a student's enrolled sections
    and taken/applied sections by the selected program — Issue #1150.

    Sections from the currently selected program appear in program_enrolled /
    program_taken; sections from all other programs are hidden in
    other_enrolled / other_taken.
    """

    def setUp(self):
        # Call super only ONCE.  Double setUp causes argcache derived-field
        # signal handlers to be re-registered, which corrupts the handler
        # chain when StudentRegistration is saved.
        super(EnrolledSplitViewTest, self).setUp()
        self.selected_program = self.program
        self.enrolled_rt = RegistrationType.objects.get(name='Enrolled')

        # Build a second program to act as the "other" program.
        self.other_program = self._create_other_program()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_other_program(self):
        """
        Create a minimal second Program with one accepted ClassSubject and
        one ClassSection, sharing modules/categories with the selected program.
        """
        other_prog = Program.objects.create(
            url='TestProgram/2020_Other',
            name='TestProgram Other 2020',
            grade_min=7,
            grade_max=12,
            director_email='info@test.learningu.org',
            program_size_max=3000,
        )
        # Share modules / categories so the view can look up module data.
        other_prog.program_modules.set(self.selected_program.program_modules.all())
        other_prog.class_categories.set(self.selected_program.class_categories.all())

        et = EventType.get_from_desc('Class Time Block')
        Event.objects.create(
            program=other_prog,
            event_type=et,
            start=datetime.datetime(2020, 7, 7, 7, 5),
            end=datetime.datetime(2020, 7, 7, 8, 0),
            short_description='Other Slot 0',
            description='07:05 07/07/2020',
        )

        other_class = ClassSubject.objects.create(
            title='Other Test Class',
            category=self.categories[0],
            grade_min=7,
            grade_max=12,
            parent_program=other_prog,
            class_size_max=30,
            class_info='Other program class for #1150 test',
        )
        other_class.makeTeacher(self.teachers[0])
        other_class.accept()
        if not other_class.get_sections().exists():
            other_class.add_section(duration=50 / 60.0)

        return other_prog

    def _enroll(self, student, section):
        """
        Insert a StudentRegistration row using bulk_create so that Django's
        post_save signal is NOT fired.  This avoids the argcache DerivedField
        handler that fires on StudentRegistration saves — that handler fails
        with ``AttributeError: 'NewCls' object has no attribute 'model'``
        when a previous test in the suite has left a broken handler in the
        signal chain (a known pre-existing issue in programprintables).
        """
        StudentRegistration.objects.bulk_create([
            StudentRegistration(
                user=student, section=section, relationship=self.enrolled_rt
            )
        ])

    # ------------------------------------------------------------------
    # Tests — program_enrolled / other_enrolled
    # ------------------------------------------------------------------

    def test_selected_program_section_appears_in_program_enrolled(self):
        """A section from the selected program must appear in program_enrolled."""
        student = self.students[0]
        admin = self.admins[0]

        selected_section = self.selected_program.sections()[0]
        self._enroll(student, selected_section)

        self.client.force_login(admin)
        response = self.client.get(
            '/manage/userview',
            {'username': student.username, 'program': self.selected_program.id},
        )
        self.assertEqual(response.status_code, 200)

        program_ids = [s.id for s in response.context['program_enrolled']]
        self.assertIn(
            selected_section.id,
            program_ids,
            "Section from the selected program must appear in program_enrolled",
        )

    def test_other_program_section_appears_in_other_enrolled(self):
        """A section from a different program must appear in other_enrolled."""
        student = self.students[0]
        admin = self.admins[0]

        other_section = self.other_program.sections()[0]
        self._enroll(student, other_section)

        self.client.force_login(admin)
        response = self.client.get(
            '/manage/userview',
            {'username': student.username, 'program': self.selected_program.id},
        )
        self.assertEqual(response.status_code, 200)

        other_ids = [s.id for s in response.context['other_enrolled']]
        self.assertIn(
            other_section.id,
            other_ids,
            "Section from a different program must appear in other_enrolled",
        )

    def test_enrolled_sections_are_not_cross_contaminated(self):
        """
        A selected-program section must NOT appear in other_enrolled, and
        a non-selected-program section must NOT appear in program_enrolled.
        """
        student = self.students[0]
        admin = self.admins[0]

        selected_section = self.selected_program.sections()[0]
        other_section = self.other_program.sections()[0]

        self._enroll(student, selected_section)
        self._enroll(student, other_section)

        self.client.force_login(admin)
        response = self.client.get(
            '/manage/userview',
            {'username': student.username, 'program': self.selected_program.id},
        )
        self.assertEqual(response.status_code, 200)

        program_ids = [s.id for s in response.context['program_enrolled']]
        other_ids = [s.id for s in response.context['other_enrolled']]

        self.assertIn(selected_section.id, program_ids)
        self.assertNotIn(
            selected_section.id, other_ids,
            "Selected-program section must not leak into other_enrolled",
        )

        self.assertIn(other_section.id, other_ids)
        self.assertNotIn(
            other_section.id, program_ids,
            "Other-program section must not leak into program_enrolled",
        )

    # ------------------------------------------------------------------
    # Tests — program_taken / other_taken
    # ------------------------------------------------------------------

    def test_selected_program_section_appears_in_program_taken(self):
        """A taken/applied section from the selected program must appear in program_taken."""
        student = self.students[0]
        admin = self.admins[0]

        selected_section = self.selected_program.sections()[0]
        self._enroll(student, selected_section)

        self.client.force_login(admin)
        response = self.client.get(
            '/manage/userview',
            {'username': student.username, 'program': self.selected_program.id},
        )
        self.assertEqual(response.status_code, 200)
        # program_taken should not contain sections from other programs
        program_taken_program_ids = {
            s.parent_class.parent_program_id for s in response.context['program_taken']
        }
        self.assertTrue(
            all(pid == self.selected_program.id for pid in program_taken_program_ids),
            "program_taken must only contain sections from the selected program",
        )

    def test_other_program_section_appears_in_other_taken(self):
        """A taken/applied section from a different program must appear in other_taken."""
        student = self.students[0]
        admin = self.admins[0]

        other_section = self.other_program.sections()[0]
        self._enroll(student, other_section)

        self.client.force_login(admin)
        response = self.client.get(
            '/manage/userview',
            {'username': student.username, 'program': self.selected_program.id},
        )
        self.assertEqual(response.status_code, 200)
        other_taken_program_ids = {
            s.parent_class.parent_program_id for s in response.context['other_taken']
        }
        self.assertTrue(
            all(pid != self.selected_program.id for pid in other_taken_program_ids),
            "other_taken must not contain sections from the selected program",
        )
