import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclasslist import (
    OnSiteClassList,
    parse_update_schedule_sections,
)
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


class ParseUpdateScheduleSectionsTests(SimpleTestCase):

    def test_rejects_non_list(self):
        with self.assertRaises(ValueError):
            parse_update_schedule_sections('{}')
        with self.assertRaises(ValueError):
            parse_update_schedule_sections('5')

    def test_dedup_cast_drop_invalid(self):
        raw = json.dumps(["1", 2, 2, "03", "abc", None])
        self.assertEqual(parse_update_schedule_sections(raw), [1, 2, 3])

    def test_rejects_all_invalid_when_nonempty(self):
        with self.assertRaises(ValueError):
            parse_update_schedule_sections(json.dumps(["abc"]))

    def test_rejects_too_many(self):
        raw = json.dumps(list(range(1, 502)))
        with self.assertRaises(ValueError):
            parse_update_schedule_sections(raw)


class UpdateScheduleJsonValidationTests(SimpleTestCase):

    def test_sections_dict_returns_400(self):
        module = SimpleNamespace()
        rf = RequestFactory()
        request = rf.get('/dummy', {'user': '123', 'sections': '{}'})

        with patch.object(ESPUser.objects, "get") as mock_get:
            mock_user = MagicMock(spec=ESPUser)
            mock_user.id = 123
            mock_user.name.return_value = "Test User"
            mock_get.return_value = mock_user

            fn = getattr(OnSiteClassList.update_schedule_json, "method", OnSiteClassList.update_schedule_json)
            response = fn(module, request, None, None, None, None, None, None)

            self.assertEqual(response.status_code, 400)
            payload = json.loads(response.content.decode('utf-8'))
            self.assertTrue(
                any('sections' in m.lower() for m in payload.get('messages', []))
            )
