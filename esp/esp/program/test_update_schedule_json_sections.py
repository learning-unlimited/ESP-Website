import json
from types import SimpleNamespace

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclasslist import (
    OnSiteClassList,
    parse_update_schedule_sections,
)


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
        request = rf.get('/dummy', {'sections': '{}'})
        response = OnSiteClassList.update_schedule_json.method(
            module, request, None, None, None, None, None, None
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertTrue(
            any('sections' in m.lower() for m in payload.get('messages', []))
        )
