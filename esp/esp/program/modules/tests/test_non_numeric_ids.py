"""Regression tests for #6106: a bad id in a URL or parameter must not crash a view."""
from django.db import transaction
from django.http import Http404
from django.test import TestCase

from esp.program.models import ClassSubject
from esp.program.tests import ProgramFrameworkTest
from esp.utils.ids import filter_by_id, get_by_id_or_404, parse_id

VIEWS_WITH_ID_IN_URL = [
    ('manage', 'accounting'),
    ('manage', 'deleteclass'),
    ('manage', 'editclass'),
    ('manage', 'review_students'),
    ('manage', 'view_app'),
    ('teach', 'app'),
    ('teach', 'apps'),
    ('teach', 'class_docs'),
    ('teach', 'class_status'),
    ('teach', 'class_students'),
    ('teach', 'section_attendance'),
    ('teach', 'section_students'),
    ('teach', 'review_student'),
    ('teach', 'review_students'),
    ('onsite', 'attendance'),
    ('onsite', 'section_attendance'),
    ('learn', 'ajax_clearslot'),
    ('learn', 'class_docs'),
    ('learn', 'clearslot'),
]

# Not a number, and a number that matches nothing.
BAD_IDS = ('abc', '999999')


class IdHelpersTest(TestCase):
    def test_parse_id_accepts_integers(self):
        self.assertEqual(parse_id('42'), 42)
        self.assertEqual(parse_id(7), 7)

    def test_parse_id_rejects_non_integers(self):
        for bad in ('abc', '', '12abc', '1.5', None):
            self.assertIsNone(parse_id(bad), repr(bad))

    def test_get_by_id_or_404_rejects_bad_ids(self):
        for bad in ('abc', 999999):
            with self.assertRaises(Http404):
                get_by_id_or_404(ClassSubject, bad)

    def test_filter_by_id_non_numeric_is_empty(self):
        self.assertFalse(filter_by_id(ClassSubject.objects, 'abc').exists())


class BadIdInUrlTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp(num_students=2, num_teachers=2, classes_per_teacher=1)
        self.add_user_profiles()
        self.schedule_randomly()
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))

    def url(self, section, view, extra=''):
        url = '/%s/%s/%s' % (section, self.program.getUrlBase(), view)
        if extra != '':
            url += '/%s' % extra
        return url

    def raised(self, method, url, data=None):
        """Describe any unhandled exception the request raises, or return None."""
        try:
            with transaction.atomic():
                getattr(self.client, method)(url, data or {})
        except Exception as e:
            return '%s %s -> %s: %s' % (method.upper(), url, type(e).__name__, e)
        return None

    def assert_nothing_raises(self, requests):
        errors = [err for err in (self.raised(*r) for r in requests) if err]
        self.assertEqual(errors, [], 'requests that raise on a bad id')

    def test_bad_id_in_url_does_not_crash(self):
        self.assert_nothing_raises([
            ('get', self.url(section, view, bad_id))
            for bad_id in BAD_IDS
            for section, view in VIEWS_WITH_ID_IN_URL
        ])

    def test_bad_id_in_request_parameter_does_not_crash(self):
        slot = self.program.getTimeSlots()[0]
        requests = []
        for view in ('clearslot', 'ajax_clearslot'):
            requests.append(('get', self.url('learn', view, slot.id), {'sec_id': 'abc'}))
        for section in ('teach', 'onsite'):
            requests.append(('get', self.url(section, 'section_attendance', slot.id), {'secid': 'abc'}))
        for view in ('class_status', 'class_students', 'class_docs'):
            requests.append(('post', self.url('teach', view), {'clsid': 'abc'}))
        requests.append(('post', self.url('learn', 'class_docs'), {'clsid': 'abc'}))
        requests.append(('post', self.url('teach', 'section_students'), {'secid': 'abc'}))
        self.assert_nothing_raises(requests)

    def test_accounting_unknown_user_id_is_404(self):
        for bad_id in BAD_IDS:
            response = self.client.get(self.url('manage', 'accounting', bad_id))
            self.assertEqual(response.status_code, 404, bad_id)

    def test_accounting_valid_user_id_still_works(self):
        response = self.client.get(self.url('manage', 'accounting', self.students[0].id))
        self.assertEqual(response.status_code, 200)
