from __future__ import absolute_import
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.tests.util import user_role_setup
from esp.users.forms.user_reg import ValidHostEmailField
from esp.users.models import User, ESPUser, UserForwarder, StudentInfo, Permission
from django.test import TestCase
from django.test.client import RequestFactory
import esp.users.views as views
from esp.program.models import Program

import random
import string

from esp.users.controllers.usersearch import UserSearchController


class TestUserSearchController(ProgramFrameworkTest):

    def setUp(self):
        super(TestUserSearchController, self).setUp()
        self.add_user_profiles()
        self.controller = UserSearchController()

    def _get_combination_post_data(self, list_a, list_b):
        return {
            'username': '',
            'checkbox_and_confirmed': '',
            'first_name': '',
            'last_name': '',
            'school': '',
            'use_checklist': '0',
            'gradyear_max': '',
            'userid': '',
            'zipcode': '',
            'combo_base_list': '%s:%s' % (list_a, list_b),
            'email': '',
            'states': '',
            'zipdistance': '',
            'grade_min': '',
            'gradyear_min': '',
            'checkbox_and_attended': '',
            'grade_max': '',
            'student_sendto_self': '1',
            'zipdistance_exclude': '',
        }

    def test_student_confirmed(self):
        post_data = self._get_combination_post_data('Student', 'confirmed')
        query_result = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertEqual(query_result.model, ESPUser)
        self.assertGreaterEqual(query_result.count(), 0)

    def test_teacher_interview(self):
        post_data = self._get_combination_post_data('Teacher', 'interview')
        query_result = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertEqual(query_result.model, ESPUser)
        self.assertGreaterEqual(query_result.count(), 0)

    def test_teacher_classroom_tables_query_from_post(self):
        post_data = self._get_combination_post_data('Teacher', 'all')
        query = self.controller.query_from_postdata(self.program, post_data)
        self.assertIsNotNone(query)
        result = query.getList(ESPUser)
        self.assertEqual(result.model, ESPUser)
        self.assertGreater(result.count(), 0)


class TestAutoSubmitCreateFilter(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2)
        self.add_student_profiles()
        self.controller = UserSearchController()
        self.factory = RequestFactory()

    def _make_get(self, params):
        request = self.factory.get('/manage/test/printables', params)
        request.user = self.admins[0]
        return request

    def _make_post(self, params):
        request = self.factory.post('/manage/test/printables', params)
        request.user = self.admins[0]
        return request

    def test_auto_submit_returns_filter(self):
        request = self._make_get({
            'auto_submit': 'true',
            'recipient_type': 'Student',
            'base_list': 'enrolled',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertTrue(found)
        users = result.getList(ESPUser)
        self.assertEqual(users.model, ESPUser)

    def test_auto_submit_teacher_list(self):
        request = self._make_get({
            'auto_submit': 'true',
            'recipient_type': 'Teacher',
            'base_list': 'class_approved',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertTrue(found)
        users = result.getList(ESPUser)
        self.assertEqual(users.model, ESPUser)

    def test_auto_submit_combo_list(self):
        request = self._make_get({
            'auto_submit': 'true',
            'combo_base_list': 'Teacher:class_approved',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertTrue(found)

    def test_auto_submit_false_falls_through(self):
        request = self._make_get({
            'auto_submit': 'false',
            'recipient_type': 'Student',
            'base_list': 'enrolled',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertFalse(found)

    def test_get_without_auto_submit_shows_form(self):
        request = self._make_get({
            'recipient_type': 'Student',
            'base_list': 'enrolled',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertFalse(found)

    def test_auto_submit_missing_base_list_falls_through(self):
        request = self._make_get({
            'auto_submit': 'true',
            'recipient_type': 'Student',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertFalse(found)

    def test_auto_submit_missing_recipient_type_falls_through(self):
        request = self._make_get({
            'auto_submit': 'true',
            'base_list': 'enrolled',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertFalse(found)

    def test_auto_submit_empty_params_falls_through(self):
        request = self._make_get({'auto_submit': 'true'})
        result, found = self.controller.create_filter(request, self.program)
        self.assertFalse(found)

    def test_post_still_works(self):
        request = self._make_post({
            'recipient_type': 'Student',
            'base_list': 'enrolled',
            'use_checklist': '0',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertTrue(found)
        users = result.getList(ESPUser)
        self.assertEqual(users.model, ESPUser)

    def test_auto_submit_strips_param_from_data(self):
        request = self._make_get({
            'auto_submit': 'true',
            'recipient_type': 'Student',
            'base_list': 'enrolled',
        })
        result, found = self.controller.create_filter(request, self.program)
        self.assertTrue(found)
        self.assertNotIn('auto_submit', result.useful_name)
