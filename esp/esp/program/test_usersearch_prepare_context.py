from unittest.mock import patch

from esp.program.tests import ProgramFrameworkTest
from esp.users.controllers.usersearch import UserSearchController


class UserSearchPrepareContextTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.controller = UserSearchController()

    def test_prepare_context_uses_list_metadata_instead_of_query_lists(self):
        with patch.object(self.program, 'students', side_effect=AssertionError('students() should not be called when rendering the selector')):
            with patch.object(self.program, 'teachers', side_effect=AssertionError('teachers() should not be called when rendering the selector')):
                with patch.object(self.program, 'volunteers', side_effect=AssertionError('volunteers() should not be called when rendering the selector')):
                    context = self.controller.prepare_context(self.program)

        self.assertIn('lists', context)
        self.assertIn('Teacher', context['lists'])
        self.assertIn('Student', context['lists'])
        self.assertTrue(any(item['name'] == 'class_approved' for item in context['lists']['Teacher']))
        self.assertTrue(any(item['name'] == 'enrolled' for item in context['lists']['Student']))

    def test_query_from_postdata_caches_query_lists_per_user_type(self):
        post_data = {
            'combo_base_list': 'Teacher:class_approved',
            'checkbox_or_class_rejected': 'on',
            'username': '',
            'first_name': '',
            'last_name': '',
            'email': '',
            'school': '',
            'userid': '',
            'zipcode': '',
            'zipdistance': '',
            'zipdistance_exclude': '',
            'states': '',
            'grade_min': '',
            'grade_max': '',
            'gradyear_min': '',
            'gradyear_max': '',
            'use_checklist': '0',
        }

        with patch.object(self.program, 'teachers', wraps=self.program.teachers) as mock_teachers:
            query = self.controller.query_from_postdata(self.program, post_data)

        self.assertIsNotNone(query)
        self.assertEqual(mock_teachers.call_count, 1)
