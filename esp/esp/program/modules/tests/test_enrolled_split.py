from __future__ import absolute_import

import datetime

from esp.tests.util import CacheFlushTestCase
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import Program, ClassSubject, StudentRegistration, RegistrationType
from esp.cal.models import Event, EventType


class EnrolledSplitViewTest(ProgramFrameworkTest, CacheFlushTestCase):
    """
    Tests that /manage/userview correctly splits a student's enrolled sections
    into current_enrolled (program end in the future) and past_enrolled
    (program end in the past) — Issue #1150.
    """

    def setUp(self):
        # Call super only ONCE.  Double setUp causes argcache derived-field
        # signal handlers to be re-registered, which corrupts the handler
        # chain when StudentRegistration is saved.
        super(EnrolledSplitViewTest, self).setUp()
        # self.program has Class Time Block events in 2222 (future)
        self.current_program = self.program
        self.enrolled_rt = RegistrationType.objects.get(name='Enrolled')

        # Build a minimal past program manually — no second super().setUp().
        self.past_program = self._create_past_program()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _create_past_program(self):
        """
        Create a bare Program with a past-dated 'Class Time Block' event,
        one accepted ClassSubject, and one ClassSection.
        Returns the Program instance.
        """
        past_prog = Program.objects.create(
            url='TestProgram/2020_Past',
            name='TestProgram Past 2020',
            grade_min=7,
            grade_max=12,
            director_email='info@test.learningu.org',
            program_size_max=3000,
        )
        # Share modules / categories with the current program so the view
        # can look up module data without crashing.
        past_prog.program_modules.set(self.current_program.program_modules.all())
        past_prog.class_categories.set(self.current_program.class_categories.all())

        # Past-dated Class Time Block event (same event_type used by getTimeSlots)
        et = EventType.get_from_desc('Class Time Block')
        Event.objects.create(
            program=past_prog,
            event_type=et,
            start=datetime.datetime(2020, 7, 7, 7, 5),
            end=datetime.datetime(2020, 7, 7, 8, 0),
            short_description='Past Slot 0',
            description='07:05 07/07/2020',
        )

        # One accepted class with one section
        past_class = ClassSubject.objects.create(
            title='Past Test Class',
            category=self.categories[0],
            grade_min=7,
            grade_max=12,
            parent_program=past_prog,
            class_size_max=30,
            class_info='Past class for #1150 test',
        )
        past_class.makeTeacher(self.teachers[0])
        past_class.accept()
        if not past_class.get_sections().exists():
            past_class.add_section(duration=50 / 60.0)

        return past_prog

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

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

    def test_current_section_appears_in_current_enrolled(self):
        """A section from a future program must appear in current_enrolled."""
        student = self.students[0]
        admin = self.admins[0]

        current_section = self.current_program.sections()[0]
        self._enroll(student, current_section)

        self.client.force_login(admin)
        response = self.client.get('/manage/userview', {'username': student.username})
        self.assertEqual(response.status_code, 200)

        current_ids = [s.id for s in response.context['current_enrolled']]
        self.assertIn(
            current_section.id,
            current_ids,
            "Section from a future program must appear in current_enrolled",
        )

    def test_past_section_appears_in_past_enrolled(self):
        """A section from a past program must appear in past_enrolled."""
        student = self.students[0]
        admin = self.admins[0]

        past_section = self.past_program.sections()[0]
        self._enroll(student, past_section)

        self.client.force_login(admin)
        response = self.client.get('/manage/userview', {'username': student.username})
        self.assertEqual(response.status_code, 200)

        past_ids = [s.id for s in response.context['past_enrolled']]
        self.assertIn(
            past_section.id,
            past_ids,
            "Section from a past program must appear in past_enrolled",
        )

    def test_sections_are_not_cross_contaminated(self):
        """
        A current-program section must NOT leak into past_enrolled, and
        a past-program section must NOT leak into current_enrolled.
        """
        student = self.students[0]
        admin = self.admins[0]

        current_section = self.current_program.sections()[0]
        past_section = self.past_program.sections()[0]

        self._enroll(student, current_section)
        self._enroll(student, past_section)

        self.client.force_login(admin)
        response = self.client.get('/manage/userview', {'username': student.username})
        self.assertEqual(response.status_code, 200)

        current_ids = [s.id for s in response.context['current_enrolled']]
        past_ids = [s.id for s in response.context['past_enrolled']]

        self.assertIn(current_section.id, current_ids)
        self.assertNotIn(
            current_section.id, past_ids,
            "Current section must not leak into past_enrolled",
        )

        self.assertIn(past_section.id, past_ids)
        self.assertNotIn(
            past_section.id, current_ids,
            "Past section must not leak into current_enrolled",
        )
