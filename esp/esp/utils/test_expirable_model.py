from datetime import datetime, timedelta

from django.test import TestCase

from esp.users.models import Permission


class ExpirableModelUnexpireTest(TestCase):
    def test_unexpire_with_null_start_date(self):
        p = Permission(start_date=None, end_date=datetime.now() - timedelta(days=1))
        p.unexpire(save=False)  # previously raised TypeError
        self.assertIsNone(p.end_date)
        self.assertIsNone(p.start_date)

    def test_unexpire_pulls_future_start_date_back(self):
        p = Permission(start_date=datetime.now() + timedelta(days=5),
                       end_date=datetime.now() + timedelta(days=10))
        before = datetime.now()
        p.unexpire(save=False)
        self.assertIsNone(p.end_date)
        self.assertGreaterEqual(p.start_date, before)
        self.assertLessEqual(p.start_date, datetime.now())

    def test_unexpire_keeps_past_start_date(self):
        past = datetime.now() - timedelta(days=5)
        p = Permission(start_date=past, end_date=datetime.now() - timedelta(days=1))
        p.unexpire(save=False)
        self.assertIsNone(p.end_date)
        self.assertEqual(p.start_date, past)
