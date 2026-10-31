"""
Behavioral tests for AdminReviewApps (esp/program/modules/handlers/adminreviewapps.py).

accept_student() and reject_student() create and expire StudentRegistration
objects with relationship='Accepted'.

Refs: #3780, #3773
"""

from urllib.parse import urlencode

from esp.program.models import (
    ClassSubject, RegistrationType, StudentApplication, StudentAppReview,
    StudentRegistration,
)
from esp.program.modules.handlers.adminreviewapps import AdminReviewApps
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
        # accept_student() gets class from ?cls= and passes extra to review_students()
        return self.get_module_url('manage', 'accept_student') + \
               f'/{self.cls.id}?cls={self.cls.id}&student={self.student.id}'

    def _reject_url(self):
        # reject_student() gets class from ?cls= and passes extra to review_students()
        return self.get_module_url('manage', 'reject_student') + \
               f'/{self.cls.id}?cls={self.cls.id}&student={self.student.id}'

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


class AdminReviewAppsViewsTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """Roster, view_app, error handling and schedule helpers."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        classes = list(ClassSubject.objects.filter(parent_program=self.program).order_by('id'))
        self.cls, self.other_cls = classes[0], classes[1]
        self.section = self.cls.get_sections()[0]
        self.accepted_rt, _ = RegistrationType.objects.get_or_create(
            name='Accepted', defaults={'category': 'student'}
        )
        self.enrolled_rt, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', defaults={'category': 'student'}
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _register(self, student, rtype, section=None):
        return StudentRegistration.objects.create(
            user=student, section=section or self.section, relationship=rtype)

    def _apply(self, student):
        return StudentApplication.objects.create(program=self.program, user=student)

    def _url(self, view, extra=None, **params):
        url = self.get_module_url('manage', view)
        if extra is not None:
            url += '/%s' % extra
        if params:
            url += '?' + urlencode(params)
        return url

    def _roster(self):
        response = self.client.get(self._url('review_students', self.cls.id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/adminreviewapps/roster.html')
        return response

    def assert_esp_error(self, response, message):
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'error.html')
        self.assertIn(message, str(response.context['error']))

    # ------------------------------------------------------------------
    # review_students
    # ------------------------------------------------------------------

    def test_review_students_lists_only_applicants(self):
        """Only students registered for the class who have an application
        for this program appear on the roster."""
        applicant, non_applicant, other_class_applicant = self.students[:3]
        self._register(applicant, self.enrolled_rt)
        self._register(non_applicant, self.enrolled_rt)
        self._register(other_class_applicant, self.enrolled_rt,
                       section=self.other_cls.get_sections()[0])
        self._apply(applicant)
        self._apply(other_class_applicant)

        self.login_as('admin')
        response = self._roster()

        self.assertEqual(response.context['class'], self.cls)
        students = response.context['students']
        self.assertEqual([s.id for s in students], [applicant.id])
        self.assertEqual(students[0].status, 'Not accepted')
        self.assertIsNotNone(students[0].added_class)
        self.assertEqual(students[0].app.user_id, applicant.id)

    def test_review_students_reports_accepted_status(self):
        accepted, pending = self.students[:2]
        self._register(accepted, self.accepted_rt)
        self._register(pending, self.enrolled_rt)
        self._apply(accepted)
        self._apply(pending)

        self.login_as('admin')
        statuses = {s.id: s.status for s in self._roster().context['students']}

        self.assertEqual(statuses, {accepted.id: 'Accepted', pending.id: 'Not accepted'})

    def test_review_students_sorted_by_last_name(self):
        names = ['Zimmer', 'Adams', 'Moore']
        for student, last_name in zip(self.students, names):
            student.last_name = last_name
            student.save()
            self._register(student, self.enrolled_rt)
            self._apply(student)

        self.login_as('admin')
        students = self._roster().context['students']

        self.assertEqual([s.last_name for s in students], sorted(names))

    def test_review_students_shows_class_and_program_wide_reviews_only(self):
        """Reviews for this class and program-wide reviews are shown; reviews
        attached to a different class are not."""
        student = self.students[0]
        self._register(student, self.enrolled_rt)
        app = self._apply(student)
        this_class = StudentAppReview.objects.create(
            reviewer=self.admin, class_subject=self.cls, score=10, comments='this class')
        program_wide = StudentAppReview.objects.create(
            reviewer=self.admin, class_subject=None, score=5, comments='program wide')
        other_class = StudentAppReview.objects.create(
            reviewer=self.admin, class_subject=self.other_cls, score=1, comments='other class')
        app.reviews.add(this_class, program_wide, other_class)

        self.login_as('admin')
        [listed] = self._roster().context['students']

        self.assertEqual(
            {r.id for r in listed.app_reviews}, {this_class.id, program_wide.id})

    def test_review_students_invalid_class_id(self):
        self.login_as('admin')
        for bad_id in ['abc', '999999']:
            with self.subTest(bad_id=bad_id):
                response = self.client.get(self._url('review_students', bad_id))
                self.assert_esp_error(response, 'Cannot find class.')

    def test_student_cannot_review_students(self):
        self.login_as('student')
        response = self.client.get(self._url('review_students', self.cls.id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    # ------------------------------------------------------------------
    # accept_student / reject_student
    # ------------------------------------------------------------------

    def test_accept_student_is_idempotent_and_shows_accepted_on_roster(self):
        student = self.students[0]
        self._apply(student)
        self.login_as('admin')
        url = self._url('accept_student', self.cls.id, cls=self.cls.id, student=student.id)

        self.client.get(url)
        response = self.client.get(url)

        self.assertEqual(
            StudentRegistration.objects.filter(
                user=student, section=self.section, relationship=self.accepted_rt).count(),
            1)
        self.assertTemplateUsed(response, 'program/modules/adminreviewapps/roster.html')
        self.assertEqual(
            [(s.id, s.status) for s in response.context['students']],
            [(student.id, 'Accepted')])

    def test_accept_student_bad_ids(self):
        self.login_as('admin')
        student = self.students[0]
        cases = [
            {'cls': self.cls.id, 'student': 999999},
            {'cls': 999999, 'student': student.id},
            {'cls': self.cls.id, 'student': 'abc'},
            {'cls': self.cls.id},
        ]
        for params in cases:
            with self.subTest(params=params):
                response = self.client.get(self._url('accept_student', self.cls.id, **params))
                self.assert_esp_error(response, 'Student or class not found.')
        self.assertFalse(
            StudentRegistration.objects.filter(relationship=self.accepted_rt).exists())

    def test_reject_student_keeps_other_registrations(self):
        """reject_student only expires the target student's Accepted
        registration; their enrollment and other students are untouched."""
        student, other = self.students[:2]
        enrolled = self._register(student, self.enrolled_rt)
        self._register(student, self.accepted_rt)
        self._register(other, self.accepted_rt)
        self._apply(student)
        self._apply(other)

        self.login_as('admin')
        response = self.client.get(
            self._url('reject_student', self.cls.id, cls=self.cls.id, student=student.id))

        valid = StudentRegistration.valid_objects()
        self.assertFalse(valid.filter(user=student, relationship=self.accepted_rt).exists())
        self.assertTrue(valid.filter(id=enrolled.id).exists())
        self.assertTrue(valid.filter(user=other, relationship=self.accepted_rt).exists())
        statuses = {s.id: s.status for s in response.context['students']}
        self.assertEqual(statuses[student.id], 'Not accepted')
        self.assertEqual(statuses[other.id], 'Accepted')

    def test_reject_student_unknown_ids(self):
        accepted = self._register(self.students[0], self.accepted_rt)
        self.login_as('admin')
        for params in [{'cls': self.cls.id, 'student': 999999},
                       {'cls': 999999, 'student': self.students[0].id}]:
            with self.subTest(params=params):
                response = self.client.get(self._url('reject_student', self.cls.id, **params))
                self.assert_esp_error(response, 'Student or class not found.')
        self.assertTrue(StudentRegistration.valid_objects().filter(id=accepted.id).exists())

    # ------------------------------------------------------------------
    # view_app
    # ------------------------------------------------------------------

    def test_view_app_renders_application(self):
        student = self.students[0]
        self._register(student, self.enrolled_rt)
        app = self._apply(student)
        self.login_as('admin')

        response = self.client.get(self._url('view_app', self.cls.id, student=student.id))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/adminreviewapps/app_popup.html')
        self.assertEqual(response.context['class'], self.cls)
        self.assertEqual(response.context['student'].app, app)

    def test_view_app_accepts_student_via_post(self):
        student = self.students[0]
        self._register(student, self.enrolled_rt)
        self._apply(student)
        self.login_as('admin')

        response = self.client.post(self._url('view_app', self.cls.id), {'student': student.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'].id, student.id)

    def test_view_app_errors(self):
        registered_no_app, unregistered_applicant = self.students[:2]
        self._register(registered_no_app, self.enrolled_rt)
        self._apply(unregistered_applicant)
        self.login_as('admin')
        cases = [
            ('abc', registered_no_app.id, 'Cannot find class.'),
            (self.cls.id, 999999, 'Cannot find student'),
            (self.cls.id, unregistered_applicant.id, 'Student not a student of this class.'),
            (self.cls.id, registered_no_app.id, 'Student did not apply.'),
        ]
        for extra, student_id, message in cases:
            with self.subTest(message=message):
                response = self.client.get(self._url('view_app', extra, student=student_id))
                self.assert_esp_error(response, message)

    def test_view_app_missing_or_non_numeric_student(self):
        """A missing or non-numeric student id gets the usual error page,
        not a 500 from an unhandled ValueError (#6224)."""
        self.login_as('admin')
        cases = [
            ('non-numeric', {'student': 'abc'}),
            ('missing', {}),
        ]
        for label, params in cases:
            with self.subTest(label):
                response = self.client.get(self._url('view_app', self.cls.id, **params))
                self.assert_esp_error(response, 'Cannot find student')

    def test_student_cannot_view_app(self):
        self.login_as('student')
        response = self.client.get(
            self._url('view_app', self.cls.id, student=self.students[0].id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    # ------------------------------------------------------------------
    # prepare / get_msg_vars / getSchedule
    # ------------------------------------------------------------------

    def test_prepare_lists_program_classes(self):
        module = self.get_module_obj('AdminReviewApps')
        context = module.prepare({})
        self.assertEqual(
            {c.id for c in context['classes_to_review']},
            {c.id for c in self.program.classes()})

    def test_schedule_lists_only_accepted_classes(self):
        student = self.students[0]
        self._register(student, self.accepted_rt)
        self._register(student, self.enrolled_rt, section=self.other_cls.get_sections()[0])
        module = self.get_module_obj('AdminReviewApps')

        schedule = module.get_msg_vars(student, 'schedule_app')

        self.assertEqual(schedule, AdminReviewApps.getSchedule(self.program, student))
        self.assertIn('Student schedule for %s' % student.name(), schedule)
        self.assertIn(self.cls.title, schedule)
        self.assertNotIn(self.other_cls.title, schedule)
        self.assertIsNone(module.get_msg_vars(student, 'unknown_key'))

    def test_schedule_shows_rooms_when_scheduled(self):
        student = self.students[0]
        self._register(student, self.accepted_rt)
        unscheduled_row = AdminReviewApps.getSchedule(self.program, student).splitlines()[-1]
        self.assertTrue(unscheduled_row.endswith('|N/A'))

        room = self.rooms[0]
        self.section.assign_start_time(self.timeslots[0])
        self.section.assign_room(room)
        scheduled_row = AdminReviewApps.getSchedule(self.program, student).splitlines()[-1]

        self.assertTrue(scheduled_row.endswith('|%s' % room.name))
        self.assertIn(self.section.friendly_times()[0], scheduled_row)
