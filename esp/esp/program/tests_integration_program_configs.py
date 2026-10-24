"""
Full-pipeline integration tests across multiple program configurations.

test_classreg_controller.py, test_lottery_controller.py, and
test_studentreg_controller.py test individual controllers directly, against
one fixed program configuration.

This file exercises the same registration pipeline through real views and
real HTTP requests instead, across configurations that differ the way real
programs do: capacity, grade range, timeslot count, and whether a waitlist
is offered. This catches bugs that only show up when the layers are glued
together, which single-layer tests can't see.
"""

from esp.program.controllers.lottery import LotteryAssignmentController
from esp.program.models import (
    ClassSubject,
    RegistrationProfile,
    RegistrationType,
    StudentRegistration,
)
from esp.program.modules.base import ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record, StudentInfo
from esp.tests.util import CacheFlushTestCase


# ---------------------------------------------------------------------------
# Lottery pipeline across configurations
# ---------------------------------------------------------------------------

class LotteryPipelineConfigMatrixTest(CacheFlushTestCase):
    """Runs compute_assignments() + save_assignments() to completion and
    checks the resulting DB state -- not the controller's internal numpy
    arrays -- against real capacity/timeslot/grade queries, across several
    distinct program configurations.

    Each test method builds its own program (a fresh ProgramFrameworkTest
    instance) since the configurations differ in setUp() kwargs.
    """

    def _build_program(self, **kwargs):
        pf = ProgramFrameworkTest()
        pf.setUp(**kwargs)
        return pf

    def _add_priority_and_interest(self, pf, priority_rt, interested_rt, grade_by_index=None):
        """Give every student a profile plus a Priority/1 and an Interested SR.

        grade_by_index, if given, maps student index -> grade; otherwise all
        students get grade 9 (the middle of the default 7-12 program range).
        """
        schoolyear = ESPUser.program_schoolyear(pf.program)
        sections = list(pf.program.sections().filter(meeting_times__isnull=False).distinct())
        self.assertTrue(sections, 'Test requires at least one scheduled section')

        for i, student in enumerate(pf.students):
            grade = grade_by_index[i] if grade_by_index else 9
            si = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(grade, schoolyear))
            si.save()
            RegistrationProfile(user=student, student_info=si, most_recent_profile=True).save()

            # Priority pick and a distinct interested pick, so both matrices are populated.
            pri_section = sections[i % len(sections)]
            StudentRegistration.objects.get_or_create(
                user=student, section=pri_section, relationship=priority_rt)
            int_section = sections[(i + 1) % len(sections)]
            if int_section != pri_section:
                StudentRegistration.objects.get_or_create(
                    user=student, section=int_section, relationship=interested_rt)

    def _run_lottery(self, pf):
        ctrl = LotteryAssignmentController(pf.program)
        ctrl.compute_assignments()
        ctrl.save_assignments()

    def _assert_no_overcapacity(self, pf):
        """Every section's real Enrolled count is within its saved capacity."""
        for section in pf.program.sections():
            enrolled = StudentRegistration.valid_objects().filter(
                section=section, relationship__name='Enrolled').count()
            self.assertLessEqual(
                enrolled, section.capacity,
                f'Section {section.id} enrolled {enrolled} > capacity {section.capacity}')

    def _assert_no_timeslot_conflicts(self, pf):
        """No student holds two Enrolled sections that share a real timeslot Event."""
        for student in pf.students:
            enrolled_sections = list(StudentRegistration.valid_objects().filter(
                user=student, relationship__name='Enrolled').values_list('section', flat=True))
            seen_timeslots = set()
            for section_id in enrolled_sections:
                for ts_id in pf.program.sections().get(id=section_id).meeting_times.values_list('id', flat=True):
                    self.assertNotIn(
                        ts_id, seen_timeslots,
                        f'Student {student.id} double-booked at timeslot {ts_id}')
                    seen_timeslots.add(ts_id)

    def _assert_grade_range_respected(self, pf):
        """Every Enrolled student's real getGrade() falls within the class's saved range."""
        for sr in StudentRegistration.valid_objects().filter(
                user__in=pf.students, relationship__name='Enrolled',
                section__parent_class__parent_program=pf.program):
            grade = sr.user.getGrade(pf.program)
            cls = sr.section.parent_class
            self.assertTrue(
                cls.grade_min <= grade <= cls.grade_max,
                f'Student {sr.user.id} (grade {grade}) enrolled in class '
                f'{cls.id} (range {cls.grade_min}-{cls.grade_max})')

    def test_tight_capacity_config(self):
        """More interested students than seats: no section may over-enroll."""
        pf = self._build_program(
            num_students=15, num_teachers=3, classes_per_teacher=2,
            num_timeslots=2, room_capacity=2,
            program_instance_name='3332_TightCapacity',
        )
        pf.schedule_randomly()
        priority_rt, _ = RegistrationType.objects.get_or_create(name='Priority/1')
        interested_rt, _ = RegistrationType.objects.get_or_create(name='Interested')
        self._add_priority_and_interest(pf, priority_rt, interested_rt)

        self._run_lottery(pf)

        self._assert_no_overcapacity(pf)
        self._assert_no_timeslot_conflicts(pf)

    def test_narrow_grade_window_config(self):
        """Classes restricted to a single grade: no out-of-range enrollment."""
        pf = self._build_program(
            num_students=12, num_teachers=3, classes_per_teacher=2,
            num_timeslots=3, room_capacity=6,
            program_instance_name='3333_NarrowGradeWindow',
        )
        pf.schedule_randomly()
        priority_rt, _ = RegistrationType.objects.get_or_create(name='Priority/1')
        interested_rt, _ = RegistrationType.objects.get_or_create(name='Interested')

        # Restrict half the classes to grade 11-12 only.
        classes = list(ClassSubject.objects.filter(parent_program=pf.program))
        for cls in classes[:len(classes) // 2]:
            cls.grade_min = 11
            cls.grade_max = 12
            cls.save()

        # Alternate student grades 9 and 12 so the restriction is actually exercised.
        grade_by_index = {i: (9 if i % 2 == 0 else 12) for i in range(len(pf.students))}
        self._add_priority_and_interest(pf, priority_rt, interested_rt, grade_by_index)

        self._run_lottery(pf)

        self._assert_no_overcapacity(pf)
        self._assert_grade_range_respected(pf)

    def test_many_timeslots_config(self):
        """A program with more timeslots than the other configs: same invariants hold."""
        pf = self._build_program(
            num_students=15, num_teachers=5, classes_per_teacher=2,
            num_timeslots=5, room_capacity=4,
            program_instance_name='3334_ManyTimeslots',
        )
        pf.schedule_randomly()
        priority_rt, _ = RegistrationType.objects.get_or_create(name='Priority/1')
        interested_rt, _ = RegistrationType.objects.get_or_create(name='Interested')
        self._add_priority_and_interest(pf, priority_rt, interested_rt)

        self._run_lottery(pf)

        self._assert_no_overcapacity(pf)
        self._assert_no_timeslot_conflicts(pf)
        self._assert_grade_range_respected(pf)


# ---------------------------------------------------------------------------
# First-come-first-served pipeline through the real ajax_addclass view
# ---------------------------------------------------------------------------

class FCFSPipelineIntegrationTest(ProgramFrameworkTest):
    """Registers through /learn/<prog>/ajax_addclass, the same endpoint the
    catalog page posts to, rather than calling preregister_student()
    directly. ClassSection.preregister_student() has no grade check at all --
    only ClassSubject.cannotAdd() (called by the view before it registers the
    student) enforces grade range -- so a test that skips the view cannot
    tell whether grade enforcement actually works.
    """

    def setUp(self):
        # A distinct instance_name (every other ProgramFrameworkTest subclass in
        # the suite uses the '2222_Summer' default) keeps this program's URL and
        # cached module-routing entries from colliding with another test's
        # same-named program when many test files share an xdist worker.
        super().setUp(num_students=4, num_teachers=1, classes_per_teacher=1,
                       sections_per_class=1, num_timeslots=1, room_capacity=30,
                       program_instance_name='3330_FCFSIntegration')
        self.add_user_profiles()
        self.schedule_randomly()
        self.section = self.program.sections()[0]
        self.section.parent_class.grade_min = 9
        self.section.parent_class.grade_max = 11
        self.section.parent_class.save()

    def _set_student_grade(self, student, grade):
        schoolyear = ESPUser.program_schoolyear(self.program)
        # getLastProfile() returns the student's newest profile across *all*
        # programs; getLastForProgram() scopes it to this program specifically.
        profile = RegistrationProfile.getLastForProgram(student, self.program, tl='learn')
        profile.student_info.graduation_year = ESPUser.YOGFromGrade(grade, schoolyear)
        profile.student_info.save()

    def _post_addclass(self, student):
        self.assertTrue(self.client.login(username=student.username, password='password'))
        return self.client.post(
            '/learn/%s/ajax_addclass' % self.program.getUrlBase(),
            {
                'class_id': self.section.parent_class.id,
                'section_id': self.section.id,
                'no_schedule': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def _is_enrolled(self, student):
        return StudentRegistration.valid_objects().filter(
            user=student, section=self.section, relationship__name='Enrolled').exists()

    def test_registration_succeeds_at_grade_boundaries(self):
        """Students exactly at grade_min and grade_max are accepted (inclusive range)."""
        low, high = self.students[0], self.students[1]
        self._set_student_grade(low, 9)
        self._set_student_grade(high, 11)

        for student in (low, high):
            resp = self._post_addclass(student)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(self._is_enrolled(student), f'Grade-boundary student {student.id} was not enrolled')

    def test_registration_blocked_outside_grade_range(self):
        """A student one grade below min and one grade above max are both blocked,
        and the view reports the error rather than enrolling them anyway.
        """
        below, above = self.students[0], self.students[1]
        self._set_student_grade(below, 8)
        self._set_student_grade(above, 12)

        for student in (below, above):
            resp = self._post_addclass(student)
            payload = resp.json()
            self.assertEqual(payload.get('status'), 200, f'Expected an error payload for {student.id}')
            self.assertIn('grade range', payload.get('error', ''))
            self.assertFalse(self._is_enrolled(student))

    def test_full_section_rejects_then_frees_seat_for_next_student(self):
        """A tight-capacity section rejects registration once full, and a seat
        freed by one student's drop can immediately be taken by another --
        exercising register -> full -> drop -> register as one real pipeline.
        """
        self.section.max_class_capacity = 1
        self.section.save()

        first, second = self.students[0], self.students[1]
        for student in (first, second):
            self._set_student_grade(student, 10)  # both within the class's grade range

        # First student takes the only seat.
        resp = self._post_addclass(first)
        self.assertEqual(resp.json().get('status'), True)
        self.assertTrue(self._is_enrolled(first))

        # Second student is rejected with the section's configured "full" message.
        resp = self._post_addclass(second)
        payload = resp.json()
        self.assertEqual(payload.get('status'), 200)
        self.assertEqual(payload.get('error'), self.program.studentclassregmoduleinfo.temporarily_full_text)
        self.assertFalse(self._is_enrolled(second))

        # First student drops (frees the only seat) via the real clearslot endpoint.
        timeslot_id = self.section.meeting_times.all()[0].id
        self.assertTrue(self.client.login(username=first.username, password='password'))
        resp = self.client.get(
            '/learn/%s/ajax_clearslot/%s' % (self.program.getUrlBase(), timeslot_id),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self._is_enrolled(first))

        # Second student can now take the freed seat.
        resp = self._post_addclass(second)
        self.assertEqual(resp.json().get('status'), True)
        self.assertTrue(self._is_enrolled(second))


# ---------------------------------------------------------------------------
# Waitlist toggle, through the real waitlist_subscribe view
# ---------------------------------------------------------------------------

class WaitlistToggleIntegrationTest(ProgramFrameworkTest):
    """program_allow_waitlist gates both a students()/studentDesc() bucket and
    the waitlist_subscribe view. Existing coverage (studentregmodules.py)
    only checks the bucket appears when the flag is True; this covers the
    flag being False, and the actual register-until-full-then-waitlist
    pipeline through real views rather than through a hand-created Record.
    """

    def setUp(self):
        # Only StudentRegCore + StudentClassRegModule: ProgramModuleObj.findModule()
        # routes *any* aux_call on a CoreModule (StudentRegCore is one) to the main
        # view of any other required, not-yet-completed module in the same
        # ProgramFrameworkTest default set (e.g. StudentRegPhaseZero, RegProfileModule)
        # before honoring the requested call -- so a request for waitlist_subscribe
        # can silently render an unrelated module's page instead (still HTTP 200,
        # so a status-code-only assertion would not catch it). Restricting to just
        # the two modules this test actually exercises means findRequiredModules()
        # has nothing else to redirect to.
        modules = ProgramModule.objects.filter(
            handler__in=['StudentRegCore', 'StudentClassRegModule'])
        # A distinct instance_name, for the same reason as FCFSPipelineIntegrationTest.
        super().setUp(num_students=2, num_teachers=1, classes_per_teacher=1,
                       sections_per_class=1, num_timeslots=1, room_capacity=30,
                       modules=modules, program_instance_name='3331_WaitlistIntegration')
        self.add_user_profiles()
        self.schedule_randomly()
        self.section = self.program.sections()[0]

    def _module(self):
        return self.program.getModule('StudentRegCore')

    def test_waitlist_bucket_absent_when_disabled(self):
        self.program.program_allow_waitlist = False
        self.program.save()
        self.assertNotIn('waitlisted_students', self._module().students(QObject=False))
        self.assertNotIn('waitlisted_students', self._module().studentDesc())

    def test_full_program_waitlists_the_next_student(self):
        self.program.program_allow_waitlist = True
        self.program.program_size_max = 1
        self.program.save()

        classreg_student, blocked_student = self.students[0], self.students[1]

        # First student takes the program's one seat via the real registration view.
        self.assertTrue(self.client.login(username=classreg_student.username, password='password'))
        resp = self.client.post(
            '/learn/%s/ajax_addclass' % self.program.getUrlBase(),
            {
                'class_id': self.section.parent_class.id,
                'section_id': self.section.id,
                'no_schedule': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.json().get('status'), True)
        self.assertFalse(self.program.user_can_join(blocked_student))

        # Second student is over the cap and gets waitlisted through the real view.
        self.assertTrue(self.client.login(username=blocked_student.username, password='password'))
        resp = self.client.post('/learn/%s/waitlist_subscribe' % self.program.getUrlBase(), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['already_on_list'])

        self.assertTrue(Record.objects.filter(
            user=blocked_student, program=self.program, event__name='waitlist').exists())
        self.assertIn(blocked_student, self._module().students(QObject=False)['waitlisted_students'])

        # A second visit does not create a duplicate Record.
        resp = self.client.post('/learn/%s/waitlist_subscribe' % self.program.getUrlBase(), follow=True)
        self.assertTrue(resp.context['already_on_list'])
        self.assertEqual(
            Record.objects.filter(user=blocked_student, program=self.program, event__name='waitlist').count(), 1)
