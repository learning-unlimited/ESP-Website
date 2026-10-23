from __future__ import absolute_import

import functools
import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.test.client import Client

from esp.db.autocomplete import allow_non_staff_autocomplete
from esp.db.views import autocomplete_wrapper
from esp.users.models import ESPUser, K12School


AUTOCOMPLETE_URL = '/admin/ajax_autocomplete/'

class AutocompleteAuthTest(TestCase):
    """Authentication and basic access control."""

    def setUp(self):
        self.user = ESPUser.objects.create_user(
            username='staffuser',
            email='staff@x.com',
            password='pw',
            first_name='Staff',
            last_name='User'
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
        # Unauthenticated users should be redirected to the admin login page.
        self.assertEqual(
            response.status_code, 302,
            "Unauthenticated requests should be redirected to the login page"
        )
        self.assertIn(
            '/accounts/login',
            response['Location'],
            "Unauthenticated requests should redirect to the login URL",
        )

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

    def test_invalid_model_name_returns_error(self):
        """
        Invalid model_name should not crash the view.
        """
        self.client.login(username='staffuser', password='pw')

        params = self._base_params()
        params['model_name'] = 'FakeModel'

        response = self.client.get(AUTOCOMPLETE_URL, params)
        self.assertEqual(
            response.status_code,
            400,
            "Invalid model_name should return HTTP 400, not crash"
        )


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
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_data': query,
            'prog': '',
        })
        self.assertEqual(
            response.status_code, 200,
            "Autocomplete search should return HTTP 200 OK"
        )
        return response

    def _result_ids(self, query):
        response = self._search(query)
        data = json.loads(response.content)
        return [e['id'] for e in data['result']]

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

        student_group, _ = Group.objects.get_or_create(name='Student')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        # Records the staff-only ESPUser autocompletes can actually return, so that a
        # gating regression shows up as leaked results rather than an empty query.
        self.student = ESPUser.objects.create_user(
            username='gatetest_student', email='gs@x.com', password='pw',
            first_name='Gate', last_name='Gatetest'
        )
        self.student.groups.add(student_group)
        self.teacher = ESPUser.objects.create_user(
            username='gatetest_teacher', email='gt@x.com', password='pw',
            first_name='Gate', last_name='Gatetest'
        )
        self.teacher.groups.add(teacher_group)
        self.staff = ESPUser.objects.create_user(
            username='gatetest_staff', email='gst@x.com', password='pw'
        )
        self.staff.is_staff = True
        self.staff.save()

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

    def test_non_staff_can_search_real_k12school(self):
        """The real K12School.ajax_autocomplete carries the marker, unpatched."""
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'K12School',
            'ajax_data': 'Test',
            'prog': '',
        })
        self.assertEqual(response.status_code, 200)
        ids = [r['id'] for r in json.loads(response.content)['result']]
        self.assertIn(
            K12School.objects.get(name='Test Academy').id, ids,
            "K12School.ajax_autocomplete must stay opted in for non-staff users")

    def test_non_staff_can_search_k12school(self):
        """A non-staff user can search K12School (@allow_non_staff_autocomplete)."""
        original_ajax = K12School.ajax_autocomplete.__func__

        @classmethod
        @allow_non_staff_autocomplete
        def patched_ajax(cls, data, allow_non_staff=True, **kwargs):
            # Forward any additional kwargs so the test reflects production semantics
            return original_ajax(cls, data, allow_non_staff=allow_non_staff, **kwargs)

        with patch.object(K12School, 'ajax_autocomplete', patched_ajax):
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

    def _search_espuser(self, ajax_func):
        response = self.client.get(AUTOCOMPLETE_URL, {
            'model_module': 'esp.users.models',
            'model_name': 'ESPUser',
            'ajax_func': ajax_func,
            'ajax_data': 'Gatetest',
            'prog': '',
        })
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)['result']

    def test_non_staff_cannot_search_espuser_via_kwargs_only_funcs(self):
        """Accepting **kwargs is not an opt-in to non-staff access."""
        for ajax_func in ('ajax_autocomplete_student', 'ajax_autocomplete_teacher'):
            with self.subTest(ajax_func=ajax_func):
                self.assertEqual(
                    self._search_espuser(ajax_func), [],
                    "%s takes **kwargs but is staff-only; non-staff users must "
                    "not receive results from it" % ajax_func)

    def test_staff_can_search_espuser_via_kwargs_only_funcs(self):
        """Control: the records the test above must not leak are findable by staff."""
        self.client.login(username='gatetest_staff', password='pw')
        for ajax_func, user in (('ajax_autocomplete_student', self.student),
                                ('ajax_autocomplete_teacher', self.teacher)):
            with self.subTest(ajax_func=ajax_func):
                ids = [r['id'] for r in self._search_espuser(ajax_func)]
                self.assertIn(user.id, ids)


class AutocompleteWrapperGatingTest(SimpleTestCase):
    """Non-staff access is granted by @allow_non_staff_autocomplete and nothing else."""

    def test_marked_function_opts_in(self):
        """The decorator is the opt-in."""
        @allow_non_staff_autocomplete
        def ajax_autocomplete(data):
            return ['called']

        self.assertEqual(
            autocomplete_wrapper(ajax_autocomplete, 'q', False), ['called'])

    def test_marker_survives_classmethod_binding(self):
        """The K12School shape: the marker is readable through the bound method."""
        class Model(object):
            @classmethod
            @allow_non_staff_autocomplete
            def ajax_autocomplete(cls, data, **kwargs):
                return ['called']

        self.assertEqual(
            autocomplete_wrapper(Model.ajax_autocomplete, 'q', False), ['called'])

    def test_marker_survives_decoration(self):
        """functools.wraps copies __dict__, so a wrapped autocomplete stays marked."""
        @allow_non_staff_autocomplete
        def ajax_autocomplete(data):
            return ['called']

        @functools.wraps(ajax_autocomplete)
        def wrapper(*args, **kwargs):
            return ajax_autocomplete(*args, **kwargs)

        self.assertEqual(autocomplete_wrapper(wrapper, 'q', False), ['called'])

    def test_unmarked_function_is_denied(self):
        """Without the marker non-staff get nothing, but staff still get through."""
        def ajax_autocomplete(data, **kwargs):
            return ['called']

        self.assertEqual(autocomplete_wrapper(ajax_autocomplete, 'q', False), [])
        self.assertEqual(
            autocomplete_wrapper(ajax_autocomplete, 'q', True), ['called'])

    def test_parameter_name_alone_does_not_opt_in(self):
        """Declaring an allow_non_staff parameter is not an opt-in."""
        def ajax_autocomplete(data, allow_non_staff=True):
            return ['called']

        self.assertEqual(autocomplete_wrapper(ajax_autocomplete, 'q', False), [])

    def test_marked_callable_without_signature_opts_in(self):
        """The marker is read as an attribute, so signatures need not be readable."""
        class Uninspectable(object):
            # Mirrors a C builtin, for which inspect.signature raises.
            __signature__ = 'not a signature'
            allow_non_staff = True

            def __call__(self, data, **kwargs):
                return ['called']

        self.assertEqual(
            autocomplete_wrapper(Uninspectable(), 'q', False), ['called'])

    def test_request_is_only_passed_when_accepted(self):
        """request is dropped for callees that do not declare it."""
        @allow_non_staff_autocomplete
        def wants_request(data, request=None, **kwargs):
            return ['got request'] if request is not None else ['no request']

        @allow_non_staff_autocomplete
        def no_request(data, **kwargs):
            return sorted(kwargs)

        sentinel = object()
        self.assertEqual(
            autocomplete_wrapper(wants_request, 'q', False, request=sentinel),
            ['got request'])
        self.assertEqual(
            autocomplete_wrapper(no_request, 'q', False, request=sentinel, prog=None),
            ['prog'])
