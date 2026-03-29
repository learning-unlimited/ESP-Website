from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.adminonsitewebapp import AdminOnsiteWebapp


class AdminOnsiteWebappTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _mock_section(self, **kwargs):
        base = {
            'id': 3,
            'enrolled_students': 18,
            'attending_students': 9,
            'capacity': 24,
            'teachers': [SimpleNamespace(name=lambda: 'Ada Lovelace')],
            'emailcode': lambda: 'A03',
            'title': lambda: 'Applied Cryptography',
            'prettyrooms': lambda: 'Bldg 1 / 204',
            'isRegOpen': lambda: True,
        }
        base.update(kwargs)
        return SimpleNamespace(**base)

    def test_serialize_section_has_expected_fields(self):
        section = self._mock_section()
        payload = AdminOnsiteWebapp._serialize_section(section)

        self.assertEqual(payload['section_id'], 3)
        self.assertEqual(payload['emailcode'], 'A03')
        self.assertEqual(payload['title'], 'Applied Cryptography')
        self.assertEqual(payload['teachers'], 'Ada Lovelace')
        self.assertEqual(payload['rooms'], 'Bldg 1 / 204')
        self.assertTrue(payload['registration_open'])
        self.assertEqual(payload['enrolled'], 18)
        self.assertEqual(payload['checkins'], 9)
        self.assertEqual(payload['capacity'], 24)

    def test_onsite_admin_data_returns_aggregated_counts(self):
        module = AdminOnsiteWebapp()
        module.program = SimpleNamespace()
        module._assert_program_admin = lambda request: None

        s1 = self._mock_section(enrolled_students=8, attending_students=6, capacity=10)
        s2 = self._mock_section(
            id=5,
            enrolled_students=10,
            attending_students=4,
            capacity=12,
            emailcode=lambda: 'A05',
        )

        request = self.factory.get('/onsite/test/onsite_admin_data')

        fn = getattr(AdminOnsiteWebapp.onsite_admin_data, 'method', AdminOnsiteWebapp.onsite_admin_data)
        with patch.object(AdminOnsiteWebapp, '_sections', return_value=[s1, s2]):
            resp = fn(module, request, None, 'onsite', 'x', 'y', None, None, module.program)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertIn('"total_classes": 2', resp.content.decode())
        self.assertIn('"enrolled_total": 18', resp.content.decode())
        self.assertIn('"checkins_total": 10', resp.content.decode())