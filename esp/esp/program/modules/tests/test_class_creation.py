from __future__ import absolute_import
from __future__ import division

import datetime
from decimal import Decimal

from django.test import Client
from django.test import TestCase

# CORRECT import - ProgramFrameworkTest is in tests.py (the file, not folder)
from esp.program.tests import ProgramFrameworkTest
from esp.program.models.class_ import ClassSubject

# ---------------------------------------------------------------------------
# URL helper
# ---------------------------------------------------------------------------

def _build_url(program, extra):
    """
    Build a teach-tl URL using the same pattern as other module tests:
        program.get_teach_url() -> '/teach/TestProgram/2222_Summer/'
    So the full URL is e.g. '/teach/TestProgram/2222_Summer/makeaclass'
    """
    return '{}{}'.format(program.get_teach_url(), extra)


# ---------------------------------------------------------------------------
# Shared settings mixin
# ---------------------------------------------------------------------------

class ClassCreationTestMixin(object):
    """Shared setUp settings — mixed in before ProgramFrameworkTest."""

    DEFAULT_SETTINGS = {
        'num_timeslots': 3,
        'timeslot_length': 50,
        'timeslot_gap': 10,
        'room_capacity': 30,
        'num_categories': 2,
        'num_rooms': 2,
        'num_teachers': 3,
        'classes_per_teacher': 1,
        'sections_per_class': 1,
        'num_students': 2,
        'num_admins': 1,
        'program_type': 'TestProgram',
        'program_instance_name': '2222_Summer',
        'program_instance_label': 'Summer 2222',
        'start_time': datetime.datetime(2222, 7, 7, 7, 5),
    }

    def setUp(self):
        super(ClassCreationTestMixin, self).setUp(**self.DEFAULT_SETTINGS)
        self.client = Client()

    def _ensure_subject_duration(self, subject):
        """
        Ensure ClassSubject.duration is set (required by the editclass controller).

        ClassSubject.duration is nullable; ProgramFrameworkTest only sets duration
        on sections.  The editclass controller calls float(cls.duration) before
        applying form data, so we must ensure it is set.
        """
        if not subject.duration:
            section = subject.sections.first()
            if section and section.duration:
                subject.duration = section.duration
            else:
                subject.duration = Decimal(str(self.program.getDurations()[0][0]))
            subject.save()

    def _make_valid_class_form_data(self, teacher):
        """Returns valid POST data for class creation (mirrors ProgramHappenTest)."""
        return {
            'title': 'Test Class Title',
            'category': self.categories[0].id,
            'class_info': 'A description of this class.',
            'prereqs': '',
            'duration': self.program.getDurations()[0][0],
            'num_sections': '1',
            'session_count': '1',
            'grade_min': self.program.grade_min,
            'grade_max': self.program.grade_max,
            'class_size_max': '20',
            'allow_lateness': 'False',
            'message_for_directors': '',
            'class_reg_page': '1',
            'hardness_rating': '**',
            'request-TOTAL_FORMS': '0',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
        }

    def _make_edit_form_data(self, subject):
        """Returns valid POST data for editing an existing ClassSubject.
        Uses the same required fields as the makeaclass form.
        duration comes from the program (subject.duration is None on ClassSubject).
        """
        return {
            'title': subject.title or '',
            'category': subject.category.id,
            'class_info': subject.class_info or '',
            'prereqs': '',
            'duration': self.program.getDurations()[0][0],
            'num_sections': str(subject.get_sections().count() or 1),
            'session_count': '1',
            'grade_min': subject.grade_min or self.program.grade_min,
            'grade_max': subject.grade_max or self.program.grade_max,
            'class_size_max': str(subject.class_size_max or 20),
            'allow_lateness': 'False',
            'message_for_directors': '',
            'class_reg_page': '1',
            'hardness_rating': '**',
            'request-TOTAL_FORMS': '0',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
        }


# ---------------------------------------------------------------------------
# 1. MakeAClass tests
# ---------------------------------------------------------------------------

class MakeAClassViewTest(ClassCreationTestMixin, ProgramFrameworkTest):
    """Tests for the makeaclass view (class creation form)."""

    def _makeaclass_url(self):
        return _build_url(self.program, 'makeaclass')

    def test_makeaclass_get_as_teacher_returns_200(self):
        """A logged-in teacher should be able to GET the makeaclass form."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        response = self.client.get(self._makeaclass_url())
        self.assertEqual(response.status_code, 200,
                         "Expected 200 for authenticated teacher accessing makeaclass")

    def test_makeaclass_get_unauthenticated_redirects(self):
        """An unauthenticated user should be redirected or forbidden."""
        response = self.client.get(self._makeaclass_url())
        self.assertIn(
            response.status_code, [302, 403],
            "Unauthenticated user should not access makeaclass"
        )

    def test_makeaclass_post_valid_creates_class(self):
        """A valid POST should create a new ClassSubject."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        before = ClassSubject.objects.filter(
            parent_program=self.program).count()
        self.client.post(
            self._makeaclass_url(),
            self._make_valid_class_form_data(teacher)
        )
        after = ClassSubject.objects.filter(
            parent_program=self.program).count()
        self.assertEqual(after, before + 1,
                         "Expected one new ClassSubject after valid POST")

    def test_makeaclass_teacher_set_as_owner(self):
        """The submitting teacher should be listed as a teacher of the new class."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        self.client.post(
            self._makeaclass_url(),
            self._make_valid_class_form_data(teacher)
        )
        new_class = ClassSubject.objects.filter(
            parent_program=self.program,
            title='Test Class Title'
        ).last()
        self.assertIsNotNone(new_class, "Class should have been created")
        self.assertIn(
            teacher.id,
            [t.id for t in new_class.get_teachers()],
            "Creating teacher should be listed as owner"
        )

    def test_new_class_is_unreviewed(self):
        """A newly created class should start as unreviewed/unapproved."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        self.client.post(
            self._makeaclass_url(),
            self._make_valid_class_form_data(teacher)
        )
        new_class = ClassSubject.objects.filter(
            parent_program=self.program,
            title='Test Class Title'
        ).last()
        self.assertIsNotNone(new_class, "Class should have been created")
        self.assertFalse(
            new_class.isAccepted(),
            "Newly created class should not be accepted immediately"
        )

    def test_makeaclass_missing_title_does_not_create(self):
        """A POST missing the title should not create a class."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        before = ClassSubject.objects.filter(
            parent_program=self.program).count()
        data = self._make_valid_class_form_data(teacher)
        data.pop('title')
        self.client.post(self._makeaclass_url(), data)
        after = ClassSubject.objects.filter(
            parent_program=self.program).count()
        self.assertEqual(after, before,
                         "No class should be created when title is missing")

    def test_makeaclass_invalid_grade_range_does_not_create(self):
        """grade_min > grade_max should fail form validation."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        before = ClassSubject.objects.filter(
            parent_program=self.program).count()
        data = self._make_valid_class_form_data(teacher)
        data['grade_min'] = 12
        data['grade_max'] = 7
        self.client.post(self._makeaclass_url(), data)
        after = ClassSubject.objects.filter(
            parent_program=self.program).count()
        self.assertEqual(after, before,
                         "Class with invalid grade range should not be created")


# ---------------------------------------------------------------------------
# 2. EditClass base — NO test_ methods so Django won't run it directly
# ---------------------------------------------------------------------------

class EditClassBaseTest(ClassCreationTestMixin, ProgramFrameworkTest):
    """
    Base for editclass tests.
    Contains NO test_ methods — subclass this for real test cases.
    """

    def setUp(self):
        super(EditClassBaseTest, self).setUp()
        # Teachers need registration profiles for the coteachers view to work
        # (it calls teacher.getLastProfile() internally)
        self.add_user_profiles()
        # Add availability for all teachers across all timeslots:
        #   ClassSubject.conflicts() checks `time_avail >= time_needed`;
        #   if a teacher has no availability at all, time_avail=0 and adding
        #   them as a coteacher is always rejected. Granting full availability
        #   makes conflict detection reflect actual scheduling conflicts only.
        for teacher in self.teachers:
            for ts in self.program.getTimeSlots():
                teacher.addAvailableTime(self.program, ts)
        self.subject = ClassSubject.objects.filter(
            parent_program=self.program
        ).first()
        self.assertIsNotNone(self.subject,
                             "ProgramFrameworkTest must create at least one class")
        self._ensure_subject_duration(self.subject)
        self.subject.accept()

    def _editclass_url(self, class_id=None):
        cid = class_id or self.subject.id
        return _build_url(self.program, 'editclass/{}'.format(cid))


# ---------------------------------------------------------------------------
# 3. Class status (reviewed / unreviewed)
# ---------------------------------------------------------------------------

class ClassStatusOnEditTest(EditClassBaseTest):
    """Tests for reviewed/unreviewed status after edits."""

    def test_admin_edit_keeps_class_accepted(self):
        """
        Admin editing an accepted class should keep it accepted.
        """
        self.subject.accept()
        admin = self.admins[0]
        self.assertTrue(admin.isAdministrator(),
                        "Need an admin user for this test")
        self.assertTrue(
            self.client.login(username=admin.username, password='password'),
            "Couldn't log in as admin %s" % admin.username
        )
        data = self._make_edit_form_data(self.subject)
        data['title'] = 'Modified By Admin'
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertTrue(
            self.subject.isAccepted(),
            "Class should remain accepted after admin edit"
        )


# ---------------------------------------------------------------------------
# 4. Teacher list management
# ---------------------------------------------------------------------------

class ClassTeacherListTest(EditClassBaseTest):
    """Tests for teacher list updates when editing a class."""

    def _get_other_teacher(self):
        """Return a teacher NOT currently teaching self.subject."""
        subject_ids = {t.id for t in self.subject.get_teachers()}
        return next((t for t in self.teachers
                     if t.id not in subject_ids), None)

    def test_teacher_list_unchanged_on_trivial_edit(self):
        """Teacher list should be unchanged after a trivial (no-op) edit."""
        original_ids = {t.id for t in self.subject.get_teachers()}
        teacher = self.subject.get_teachers()[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        self.client.post(
            self._editclass_url(),
            self._make_edit_form_data(self.subject)
        )
        self.subject.refresh_from_db()
        new_ids = {t.id for t in self.subject.get_teachers()}
        self.assertEqual(original_ids, new_ids,
                         "Teacher list should be unchanged after trivial edit")

    def test_add_coteacher(self):
        """
        Adding a coteacher via the /coteachers endpoint should persist to DB.
        op='add' both stages and persists via associate_teacher_with_class.
        """
        original_teacher = self.subject.get_teachers()[0]
        coteacher = self._get_other_teacher()
        if coteacher is None:
            self.skipTest("No spare teacher available")
        self.assertTrue(
            self.client.login(username=original_teacher.username, password='password'),
            "Couldn't log in as teacher %s" % original_teacher.username
        )
        url = _build_url(self.program, 'coteachers')
        # op='add' persists the coteacher directly via associate_teacher_with_class
        self.client.post(url, {
            'op': 'add',
            'clsid': self.subject.id,
            'teacher_selected': coteacher.id,
            'coteachers': '',
        })
        self.subject.refresh_from_db()
        new_ids = {t.id for t in self.subject.get_teachers()}
        self.assertIn(coteacher.id, new_ids,
                      "New coteacher should appear in teacher list")
        self.assertIn(original_teacher.id, new_ids,
                      "Original teacher should still be in list")

    def test_remove_coteacher(self):
        """
        Removing a coteacher via the /coteachers endpoint should persist to DB.
        op='del' both stages and persists via removeTeacher.
        """
        original_teacher = self.subject.get_teachers()[0]
        coteacher = self._get_other_teacher()
        if coteacher is None:
            self.skipTest("No spare teacher available")
        # Set up: add the coteacher directly on the model first
        self.subject.makeTeacher(coteacher)
        self.assertIn(coteacher.id,
                      [t.id for t in self.subject.get_teachers()],
                      "Coteacher must be set up before the test")
        self.assertTrue(
            self.client.login(username=original_teacher.username, password='password'),
            "Couldn't log in as teacher %s" % original_teacher.username
        )
        url = _build_url(self.program, 'coteachers')
        # op='del' persists the removal directly via removeTeacher
        self.client.post(url, {
            'op': 'del',
            'clsid': self.subject.id,
            'delete_coteachers': coteacher.id,
            'coteachers': str(coteacher.id),
        })
        self.subject.refresh_from_db()
        new_ids = {t.id for t in self.subject.get_teachers()}
        self.assertNotIn(coteacher.id, new_ids,
                         "Removed coteacher should not be in teacher list")

    def test_non_owner_teacher_cannot_edit_class(self):
        """A teacher not on the class should not be able to edit it."""
        non_owner = self._get_other_teacher()
        if non_owner is None:
            self.skipTest("Could not find a non-owner teacher")
        self.assertTrue(
            self.client.login(username=non_owner.username, password='password'),
            "Couldn't log in as teacher %s" % non_owner.username
        )
        data = self._make_edit_form_data(self.subject)
        data['title'] = 'Unauthorized Modification'
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        # The app may return 200 (error page) rather than redirect/403.
        # The key assertion is that the title was NOT changed.
        self.assertNotEqual(self.subject.title, 'Unauthorized Modification',
                            "Non-owner teacher must not modify the class")


# ---------------------------------------------------------------------------
# 5. Form validation
# ---------------------------------------------------------------------------

class ClassFormValidationTest(EditClassBaseTest):
    """Tests for valid and invalid edit form submissions."""

    def test_valid_submission_updates_class(self):
        """A valid POST should update the class."""
        teacher = self.subject.get_teachers()[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        data = self._make_edit_form_data(self.subject)
        data['title'] = 'Updated Valid Title'
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.title, 'Updated Valid Title',
                         "Title should be updated after valid submission")

    def test_missing_title_does_not_update(self):
        """POST missing title should not update the class."""
        teacher = self.subject.get_teachers()[0]
        original_title = self.subject.title
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        data = self._make_edit_form_data(self.subject)
        data.pop('title')
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.title, original_title,
                         "Title should be unchanged after invalid submission")

    def test_missing_category_does_not_update(self):
        """POST missing category should fail validation."""
        teacher = self.subject.get_teachers()[0]
        original_title = self.subject.title
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        data = self._make_edit_form_data(self.subject)
        data.pop('category')
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.title, original_title,
                         "Class should be unchanged when category is missing")

    def test_negative_duration_does_not_update(self):
        """POST with negative duration should fail validation."""
        teacher = self.subject.get_teachers()[0]
        original_duration = self.subject.duration
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        data = self._make_edit_form_data(self.subject)
        data['duration'] = -1
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.duration, original_duration,
                         "Duration should be unchanged after invalid submission")

    def test_invalid_grade_range_does_not_update(self):
        """grade_min > grade_max should fail validation on edit too."""
        teacher = self.subject.get_teachers()[0]
        original_min = self.subject.grade_min
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        data = self._make_edit_form_data(self.subject)
        data['grade_min'] = 12
        data['grade_max'] = 7
        self.client.post(self._editclass_url(), data)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.grade_min, original_min,
                         "Grade range should be unchanged after invalid submission")


# ---------------------------------------------------------------------------
# 6. Teacher availability consistency
# ---------------------------------------------------------------------------

class TeacherAvailabilityConsistencyTest(ClassCreationTestMixin,
                                         ProgramFrameworkTest):
    """
    Tests that teacher availability is unchanged after class creation/editing.
    """

    def _get_availability(self, teacher):
        return {ts.id for ts in teacher.getAvailableTimes(self.program)}

    def _set_all_timeslots_available(self, teacher):
        for ts in self.timeslots:
            teacher.addAvailableTime(self.program, ts)

    def test_availability_unchanged_after_class_edit(self):
        """Editing a class should not alter the teacher's available times."""
        subject = ClassSubject.objects.filter(
            parent_program=self.program).first()
        self._ensure_subject_duration(subject)
        teacher = subject.get_teachers()[0]
        self._set_all_timeslots_available(teacher)
        before = self._get_availability(teacher)

        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        url = _build_url(self.program,
                         'editclass/{}'.format(subject.id))
        self.client.post(url, self._make_edit_form_data(subject))

        after = self._get_availability(teacher)
        self.assertEqual(before, after,
                         "Availability should not change after class edit")

    def test_adding_coteacher_does_not_change_availability(self):
        """Adding a coteacher must not mutate the original teacher's availability."""
        subject = ClassSubject.objects.filter(
            parent_program=self.program).first()
        self._ensure_subject_duration(subject)
        teacher = subject.get_teachers()[0]
        self._set_all_timeslots_available(teacher)

        subject_ids = {t.id for t in subject.get_teachers()}
        coteacher = next(
            (t for t in self.teachers if t.id not in subject_ids), None
        )
        if coteacher is None:
            self.skipTest("No available coteacher to add")

        # Ensure the coteacher has availability so op='add' succeeds
        self._set_all_timeslots_available(coteacher)

        before = self._get_availability(teacher)
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )
        url = _build_url(self.program, 'coteachers')
        # op='add' persists the coteacher directly via associate_teacher_with_class
        self.client.post(url, {
            'op': 'add',
            'clsid': subject.id,
            'teacher_selected': coteacher.id,
            'coteachers': '',
        })

        # Verify the coteacher was actually added before checking availability
        subject.refresh_from_db()
        self.assertIn(
            coteacher.id,
            [t.id for t in subject.get_teachers()],
            "Coteacher should have been added to the subject"
        )

        after = self._get_availability(teacher)
        self.assertEqual(before, after,
                         "Availability should be unchanged after adding coteacher")
