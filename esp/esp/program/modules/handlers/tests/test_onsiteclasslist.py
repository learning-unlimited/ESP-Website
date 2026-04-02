import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclasslist import OnSiteClassList
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
