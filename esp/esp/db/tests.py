"""
Unit tests for the AJAX autocomplete view (issue #1452).

Covers:
- Authentication: unauthenticated requests are redirected
- Missing parameters return HTTP 400
- Result format: JSON with 'result' list of {id, ajax_str} dicts
- Limit parameter is respected
- ESPUser autocomplete: last-name, username, and ID prefix search
- Filtered variants: student-only and teacher-only autocomplete
- Non-staff access control: blocked for ESPUser, allowed for K12School
- Custom ajax_func parameter
"""

from __future__ import absolute_import

import json

from django.contrib.auth.models import Group
from django.test import TestCase
from django.test.client import Client

from esp.users.models import ESPUser, K12School


AUTOCOMPLETE_URL = '/admin/ajax_autocomplete/'


class AutocompleteAuthTest(TestCase):
    """Authentication and basic access control."""

    def setUp(self):
        self.user = ESPUser.objects.create_user(
            username='staffuser', email='staff@x.com',
            password='pw', first_name='Staff', last_name='User'
        )
        self.user.is_staff = True
        self.user.save()

    def _base_params(self):
        return {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': 'User',
            'prog': '',
        }

    def test_unauthenticated_request_redirects(self):
        """Anonymous requests should not reach the view."""
        response = Client().get(AUTOCOMPLETE_URL, self._base_params())
        self.assertNotEqual(response.status_code, 200,
                            "Unauthenticated requests should not return 200")

    def test_missing_model_module_returns_400(self):
        """Omitting model_module should return HTTP 400."""
        self.client.login(username='staffuser', password='pw')
        params = self._base_params()
        del params['model_module']
        response = self.client.get(AUTOCOMPLETE_URL, params)
        self.assertEqual(response.status_code, 400)

    def test_missing_model_name_returns_400(self):
        """Omitting model_name should return HTTP 400."""
        self.client.login(username='staffuser', password='pw')
        params = self._base_params()
        del params['model_name']
        response = self.client.get(AUTOCOMPLETE_URL, params)
        self.assertEqual(response.status_code, 400)

    def test_missing_ajax_data_returns_400(self):
        """Omitting ajax_data should return HTTP 400."""
        self.client.login(username='staffuser', password='pw')
        params = self._base_params()
        del params['ajax_data']
        response = self.client.get(AUTOCOMPLETE_URL, params)
        self.assertEqual(response.status_code, 400)


class AutocompleteResultFormatTest(TestCase):
    """Response format tests."""

    def setUp(self):
        self.staff = ESPUser.objects.create_user(
            username='staffmember', email='st@x.com',
            password='pw', first_name='Alice', last_name='Smith'
        )
        self.staff.is_staff = True
        self.staff.save()
        self.client.login(username='staffmember', password='pw')

    def _get(self, **kwargs):
        params = {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': '',
            'prog': '',
        }
        params.update(kwargs)
        return self.client.get(AUTOCOMPLETE_URL, params)

    def test_response_is_valid_json(self):
        """Response body should be valid JSON."""
        response = self._get(ajax_data='Smith')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('result', data)

    def test_result_is_list(self):
        """'result' key should map to a list."""
        response = self._get(ajax_data='Smith')
        data = json.loads(response.content)
        self.assertIsInstance(data['result'], list)

    def test_result_entry_has_id_and_ajax_str(self):
        """Each entry in 'result' should have 'id' and 'ajax_str' keys."""
        response = self._get(ajax_data='Smith')
        data = json.loads(response.content)
        for entry in data['result']:
            self.assertIn('id', entry)
            self.assertIn('ajax_str', entry)

    def test_ajax_str_contains_id_suffix(self):
        """ajax_str should end with ' (<id>)' as appended by the view."""
        response = self._get(ajax_data='Smith')
        data = json.loads(response.content)
        for entry in data['result']:
            self.assertTrue(
                entry['ajax_str'].endswith(' (%s)' % entry['id']),
                "ajax_str '%s' should end with ' (%s)'" % (entry['ajax_str'], entry['id'])
            )


class AutocompleteESPUserSearchTest(TestCase):
    """ESPUser search: by last name, first name, username, and ID prefix."""

    def setUp(self):
        self.staff = ESPUser.objects.create_user(
            username='staffsearcher', email='searcher@x.com',
            password='pw', first_name='', last_name=''
        )
        self.staff.is_staff = True
        self.staff.save()

        self.user1 = ESPUser.objects.create_user(
            username='jdoe', email='jdoe@x.com',
            password='pw', first_name='Jane', last_name='Doe'
        )
        self.user2 = ESPUser.objects.create_user(
            username='bsmith', email='bsmith@x.com',
            password='pw', first_name='Bob', last_name='Smith'
        )
        self.client.login(username='staffsearcher', password='pw')

    def _search(self, query):
        return self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': query,
            'prog': '',
        })

    def _result_ids(self, query):
        return [e['id'] for e in json.loads(self._search(query).content)['result']]

    def test_search_by_last_name(self):
        """Users can be found by last name prefix."""
        ids = self._result_ids('Doe')
        self.assertIn(self.user1.id, ids)
        self.assertNotIn(self.user2.id, ids)

    def test_search_by_last_name_case_insensitive(self):
        """Last-name search is case-insensitive."""
        ids = self._result_ids('doe')
        self.assertIn(self.user1.id, ids)

    def test_search_by_username(self):
        """Users can be found by username prefix."""
        ids = self._result_ids('bsmith')
        self.assertIn(self.user2.id, ids)

    def test_search_by_lastname_comma_firstname(self):
        """Comma-separated 'Last, First' format narrows results."""
        ids = self._result_ids('Smith, Bob')
        self.assertIn(self.user2.id, ids)
        self.assertNotIn(self.user1.id, ids)

    def test_no_results_for_unknown_query(self):
        """A query matching no users returns an empty result list."""
        ids = self._result_ids('ZZZNobodyXXX')
        self.assertEqual(ids, [])

    def test_limit_parameter_is_respected(self):
        """The 'limit' parameter caps the number of returned results."""
        # Create more users with the same last name
        for i in range(5):
            ESPUser.objects.create_user(
                username='testlimit%d' % i, email='tl%d@x.com' % i,
                password='pw', first_name='Test', last_name='Common'
            )
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': 'Common',
            'prog': '',
            'limit': '2',
        })
        data = json.loads(response.content)
        self.assertLessEqual(len(data['result']), 2)


class AutocompleteFilteredSearchTest(TestCase):
    """Tests for filtered autocomplete variants (student/teacher)."""

    def setUp(self):
        self.staff = ESPUser.objects.create_user(
            username='filterstaffuser', email='fstaff@x.com',
            password='pw', first_name='', last_name='Filter'
        )
        self.staff.is_staff = True
        self.staff.save()

        student_group, _ = Group.objects.get_or_create(name='Student')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        self.student = ESPUser.objects.create_user(
            username='studentfilter', email='stu@x.com',
            password='pw', first_name='', last_name='Filter'
        )
        self.student.groups.add(student_group)

        self.teacher = ESPUser.objects.create_user(
            username='teacherfilter', email='tea@x.com',
            password='pw', first_name='', last_name='Filter'
        )
        self.teacher.groups.add(teacher_group)

        self.client.login(username='filterstaffuser', password='pw')

    def _search(self, ajax_func, query='Filter'):
        return json.loads(self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_func': ajax_func,
            'ajax_data': query,
            'prog': '',
        }).content)['result']

    def test_student_filter_returns_students_only(self):
        """ajax_autocomplete_student should return only Student-group members."""
        results = self._search('ajax_autocomplete_student')
        ids = [r['id'] for r in results]
        self.assertIn(self.student.id, ids)
        self.assertNotIn(self.teacher.id, ids)

    def test_teacher_filter_returns_teachers_only(self):
        """ajax_autocomplete_teacher should return only Teacher-group members."""
        results = self._search('ajax_autocomplete_teacher')
        ids = [r['id'] for r in results]
        self.assertIn(self.teacher.id, ids)
        self.assertNotIn(self.student.id, ids)


class AutocompleteNonStaffAccessTest(TestCase):
    """Non-staff users are blocked from ESPUser autocomplete but allowed for K12School."""

    def setUp(self):
        self.non_staff = ESPUser.objects.create_user(
            username='regular_user', email='reg@x.com', password='pw'
        )
        self.non_staff.is_staff = False
        self.non_staff.save()
        self.client.login(username='regular_user', password='pw')

        K12School.objects.get_or_create(name='Test Academy')

    def test_non_staff_cannot_search_espuser(self):
        """A non-staff user searching ESPUser should get an empty result list."""
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': 'Test',
            'prog': '',
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], [],
                         "Non-staff users must not be able to search ESPUser records")

    def test_non_staff_can_search_k12school(self):
        """A non-staff user can search K12School (allow_non_staff=True)."""
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'K12School',
            'ajax_data': 'Test',
            'prog': '',
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        ids = [r['id'] for r in data['result']]
        school = K12School.objects.get(name='Test Academy')
        self.assertIn(school.id, ids)
