import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclasslist import OnSiteClassList
from esp.users.models import ESPUser


class UpdateScheduleJsonTests(SimpleTestCase):
    """Regression tests for update_schedule_json early failure cases."""

    def setUp(self):
        self.factory = RequestFactory()
        # The method body doesn't rely on ProgramModuleObj fields, so a stub works.
        self.module = SimpleNamespace()

    def _call(self, params):
        request = self.factory.get("/onsite/update", params)
        # Bypass the needs_onsite wrapper by calling the stored original method.
        return OnSiteClassList.update_schedule_json.method(
            self.module, request, None, None, None, None, None, None
        )

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
