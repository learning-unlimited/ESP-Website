import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclasslist import OnSiteClassList
from esp.program.models import RegistrationType, StudentRegistration
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class UpdateScheduleJsonTests(SimpleTestCase):
    """Regression tests for update_schedule_json early failure cases."""

    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace()

    def _call(self, params):
        request = self.factory.get("/onsite/update", params)
        fn = getattr(OnSiteClassList.update_schedule_json, "method", OnSiteClassList.update_schedule_json)
        return fn(self.module, request, None, None, None, None, None, None)

    def _assert_user_not_found(self, resp):
        self.assertEqual(resp.status_code, 400)
        payload = json.loads(resp.content.decode())
        self.assertEqual(payload.get("messages"), ["User not found"])
        self.assertEqual(payload.get("sections"), [])

    def test_missing_user_param_returns_400(self):
        resp = self._call({})
        self._assert_user_not_found(resp)

    def test_non_numeric_user_param_returns_400(self):
        resp = self._call({"user": "abc"})
        self._assert_user_not_found(resp)

    def test_unknown_user_id_returns_400(self):
        with patch.object(ESPUser.objects, "get", side_effect=ESPUser.DoesNotExist):
            resp = self._call({"user": "9999"})
        self._assert_user_not_found(resp)


class PrintScheduleStatusTests(SimpleTestCase):
    """Regression tests for printschedule_status early failure cases."""

    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace()

    def _call(self, params):
        request = self.factory.get("/onsite/printschedule", params)
        fn = getattr(OnSiteClassList.printschedule_status, "method", OnSiteClassList.printschedule_status)
        return fn(self.module, request, None, None, None, None, None, None)

    def _assert_user_not_found(self, resp):
        self.assertEqual(resp.status_code, 400)
        payload = json.loads(resp.content.decode())
        self.assertIn("message", payload)

    def test_missing_user_param_returns_400(self):
        resp = self._call({})
        self._assert_user_not_found(resp)

    def test_non_numeric_user_param_returns_400(self):
        resp = self._call({"user": "abc"})
        self._assert_user_not_found(resp)

    def test_unknown_user_id_returns_400(self):
        with patch.object(ESPUser.objects, "get", side_effect=ESPUser.DoesNotExist):
            resp = self._call({"user": "9999"})
        self._assert_user_not_found(resp)


class SectionDataTests(ProgramFrameworkTest):
    """Tests for OnSiteClassList.section_data"""

    def setUp(self):
        super().setUp(
            num_timeslots=1,
            num_teachers=2,
            classes_per_teacher=1,
            sections_per_class=1,
            num_rooms=2,
            num_students=0,
        )
        self.section = self.program.sections()[0]
        self.result = OnSiteClassList.section_data(self.section)

    def test_section_data_has_required_keys(self):
        """Returned dict must contain exactly the five expected keys."""
        self.assertEqual(set(self.result.keys()), {'id', 'emailcode', 'title', 'teachers', 'rooms'})

    def test_section_data_id_matches(self):
        """result['id'] must equal the section's pk."""
        self.assertEqual(self.result['id'], self.section.id)

    def test_section_data_title_matches(self):
        """result['title'] must equal section.title()."""
        self.assertEqual(self.result['title'], self.section.title())

    def test_section_data_teachers_is_string(self):
        """result['teachers'] must be a string containing at least one teacher's name."""
        self.assertIsInstance(self.result['teachers'], str)
        # section_data builds the string from list(sec.teachers)
        teachers = list(self.section.teachers)
        self.assertTrue(len(teachers) > 0, "Expected at least one teacher on this section")
        self.assertIn(teachers[0].name(), self.result['teachers'])

    def test_section_data_rooms_is_string(self):
        """result['rooms'] must be a string (may be empty if the section has no room assigned)."""
        self.assertIsInstance(self.result['rooms'], str)

    def test_section_data_emailcode_is_string(self):
        """result['emailcode'] must be a non-empty string."""
        self.assertIsInstance(self.result['emailcode'], str)
        self.assertTrue(len(self.result['emailcode']) > 0)


class CatalogStatusTests(ProgramFrameworkTest):
    """Tests for OnSiteClassList.catalog_status"""

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_teachers=2,
            classes_per_teacher=1,
            sections_per_class=1,
            num_rooms=2,
            num_students=0,
        )
        self.factory = RequestFactory()
        self.admin = self.admins[0]

    def _call(self):
        request = self.factory.get('/onsite/catalog')
        request.user = self.admin
        fn = getattr(OnSiteClassList.catalog_status, 'method', OnSiteClassList.catalog_status)
        module = SimpleNamespace()
        return fn(module, request, None, None, None, None, None, self.program)

    def test_returns_200(self):
        """catalog_status must return 200."""
        resp = self._call()
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_json(self):
        """Response Content-Type must include application/json."""
        resp = self._call()
        self.assertIn('application/json', resp['Content-Type'])

    def test_top_level_keys(self):
        """Parsed JSON body must have exactly classes, sections, timeslots, categories."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertEqual(set(data.keys()), {'classes', 'sections', 'timeslots', 'categories'})

    def test_classes_structure(self):
        """data['classes'] must be a list and first entry must have id, title, grade_min, grade_max, teacher_names."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertIsInstance(data['classes'], list)
        if data['classes']:
            entry = data['classes'][0]
            for key in ('id', 'title', 'grade_min', 'grade_max', 'teacher_names'):
                self.assertIn(key, entry)

    def test_sections_structure(self):
        """data['sections'] must be a list and first entry must have id, parent_class__id, enrolled_students, capacity."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertIsInstance(data['sections'], list)
        if data['sections']:
            entry = data['sections'][0]
            for key in ('id', 'parent_class__id', 'enrolled_students', 'capacity'):
                self.assertIn(key, entry)

    def test_timeslots_structure(self):
        """data['timeslots'] must be a list of 3-element entries; program has 2 timeslots so index 0 is safe."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertIsInstance(data['timeslots'], list)
        self.assertEqual(len(data['timeslots']), 2)
        self.assertEqual(len(data['timeslots'][0]), 3)

    def test_categories_non_empty(self):
        """data['categories'] must be non-empty; first entry must have id, symbol, category."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertGreater(len(data['categories']), 0)
        entry = data['categories'][0]
        for key in ('id', 'symbol', 'category'):
            self.assertIn(key, entry)

    def test_status_filter_excludes_rejected_class(self):
        """A class with status=-10 (rejected) must not appear in data['classes']."""
        cls = self.program.classes()[0]
        original_status = cls.status
        cls.status = -10
        cls.save()
        self.addCleanup(cls.__class__.objects.filter(pk=cls.pk).update, status=original_status)

        resp = self._call()
        data = json.loads(resp.content)
        class_ids = [c['id'] for c in data['classes']]
        self.assertNotIn(cls.id, class_ids)


class EnrollmentStatusTests(ProgramFrameworkTest):
    """Tests for OnSiteClassList.enrollment_status"""

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_teachers=2,
            classes_per_teacher=1,
            sections_per_class=1,
            num_rooms=2,
            num_students=3,
        )
        self.schedule_randomly()
        self.add_user_profiles()
        self.factory = RequestFactory()
        self.admin = self.admins[0]
        # Enrolling students into sections
        for student in self.students:
            for section in self.program.sections()[:1]:
                section.preregister_student(student)
        self.enrolled_section = self.program.sections()[0]

    def _call(self):
        request = self.factory.get('/onsite/enrollment_status')
        request.user = self.admin
        fn = getattr(OnSiteClassList.enrollment_status, 'method', OnSiteClassList.enrollment_status)
        module = SimpleNamespace()
        return fn(module, request, None, None, None, None, None, self.program)

    def test_returns_200(self):
        """enrollment_status must return 200."""
        resp = self._call()
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_json(self):
        """Response Content-Type must include application/json."""
        resp = self._call()
        self.assertIn('application/json', resp['Content-Type'])

    def test_returns_list(self):
        """Parsed JSON body must be a list."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)

    def test_enrolled_pair_appears(self):
        """[student.id, section.id] pair for an enrolled student must appear in the result."""
        resp = self._call()
        data = json.loads(resp.content)
        student = self.students[0]
        expected_pair = [student.id, self.enrolled_section.id]
        self.assertIn(expected_pair, data)

    def test_only_enrolled_relationship(self):
        """A non-Enrolled registration must not duplicate the enrolled pair."""
        # Created a Waitlisted registration for students[0] on the same section
        waitlisted_rt, _ = RegistrationType.objects.get_or_create(
            name='Waitlisted', category='student'
        )
        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.enrolled_section,
            relationship=waitlisted_rt,
        )
        resp = self._call()
        data = json.loads(resp.content)
        # The enrolled pair should appear exactly once (waitlisted is excluded)
        student = self.students[0]
        expected_pair = [student.id, self.enrolled_section.id]
        count = data.count(expected_pair)
        self.assertEqual(count, 1)

    def test_excluded_when_section_status_negative(self):
        """Students enrolled in a section with status <= 0 must not appear in the result."""
        original_status = self.enrolled_section.status
        self.enrolled_section.status = -10
        self.enrolled_section.save()
        self.addCleanup(
            self.enrolled_section.__class__.objects.filter(pk=self.enrolled_section.pk).update,
            status=original_status,
        )
        resp = self._call()
        data = json.loads(resp.content)
        user_ids_in_result = [pair[0] for pair in data]
        self.assertNotIn(self.students[0].id, user_ids_in_result)


class CountsStatusTests(ProgramFrameworkTest):
    """Tests for OnSiteClassList.counts_status"""

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_teachers=2,
            classes_per_teacher=1,
            sections_per_class=1,
            num_rooms=2,
            num_students=3,
        )
        self.schedule_randomly()
        self.add_user_profiles()
        self.factory = RequestFactory()
        self.admin = self.admins[0]
        # Enroll students into sections
        for student in self.students:
            for section in self.program.sections()[:1]:
                section.preregister_student(student)
        self.enrolled_section = self.program.sections()[0]

    def _call(self):
        request = self.factory.get('/onsite/counts_status')
        request.user = self.admin
        fn = getattr(OnSiteClassList.counts_status, 'method', OnSiteClassList.counts_status)
        module = SimpleNamespace()
        return fn(module, request, None, None, None, None, None, self.program)

    def test_returns_200(self):
        """counts_status must return 200."""
        resp = self._call()
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_json(self):
        """Response Content-Type must include application/json."""
        resp = self._call()
        self.assertIn('application/json', resp['Content-Type'])

    def test_returns_list_of_triples(self):
        """Parsed JSON body must be a list; each entry must have exactly 3 elements."""
        resp = self._call()
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)
        for entry in data:
            self.assertEqual(len(entry), 3)

    def test_triple_structure(self):
        """Each triple must have int section id, int enrolled count, int attending count."""
        resp = self._call()
        data = json.loads(resp.content)
        for entry in data:
            self.assertIsInstance(entry[0], int)
            self.assertIsInstance(entry[1], int)
            self.assertIsInstance(entry[2], int)

    def test_enrolled_count_reflects_registrations(self):
        """The enrolled count for the enrolled_section must be >= number of students enrolled."""
        resp = self._call()
        data = json.loads(resp.content)
        section_entry = next(
            (entry for entry in data if entry[0] == self.enrolled_section.id), None
        )
        self.assertIsNotNone(section_entry, "enrolled_section not found in counts_status result")
        self.assertGreaterEqual(section_entry[1], len(self.students))

    def test_status_filter(self):
        """A section with status <= 0 must not appear in the result."""
        original_status = self.enrolled_section.status
        self.enrolled_section.status = -10
        self.enrolled_section.save()
        self.addCleanup(
            self.enrolled_section.__class__.objects.filter(pk=self.enrolled_section.pk).update,
            status=original_status,
        )
        resp = self._call()
        data = json.loads(resp.content)
        section_ids = [entry[0] for entry in data]
        self.assertNotIn(self.enrolled_section.id, section_ids)
