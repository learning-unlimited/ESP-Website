import unittest
from types import SimpleNamespace
from unittest.mock import patch

from django.db.models.query import Q

from esp.middleware import ESPError_Log
from esp.users.views.usersearch import add_top_level_filter, get_user_list


class AddTopLevelFilterTest(unittest.TestCase):
    def setUp(self):
        self.query = Q(first=True)
        self.list_dict = {'second': {'list': Q(second=True)}}

    def test_no_top_level_filter_preserves_query(self):
        self.assertEqual(add_top_level_filter({}, self.list_dict, self.query),
                         self.query)

    def test_adds_and_condition(self):
        result = add_top_level_filter(
            {'top_level_operator': 'and', 'top_level_list': 'second'},
            self.list_dict,
            self.query)
        self.assertEqual(result, self.query & Q(second=True))

    def test_adds_negated_or_condition(self):
        result = add_top_level_filter(
            {'top_level_operator': 'or', 'top_level_list': 'second',
             'top_level_not': 'not'},
            self.list_dict,
            self.query)
        self.assertEqual(result, self.query | ~Q(second=True))

    def test_rejects_incomplete_or_invalid_filter(self):
        invalid_filters = [
            {'top_level_operator': 'and'},
            {'top_level_list': 'missing', 'top_level_operator': 'or'},
            {'top_level_list': 'second', 'top_level_operator': 'xor'},
            {'top_level_list': 'second', 'top_level_operator': 'or',
             'top_level_not': 'invalid'},
        ]
        for post_data in invalid_filters:
            with self.assertRaises(ESPError_Log):
                add_top_level_filter(post_data, self.list_dict, self.query)


class GetUserListTest(unittest.TestCase):
    @patch('esp.users.views.usersearch.PersistentQueryFilter.getFilterFromQ')
    @patch('esp.users.views.usersearch.getQForUser', return_value=Q(first=True))
    def test_user_list_submission_without_mailman(self, get_q_for_user,
                                                  get_filter_from_q):
        filter_object = object()
        get_filter_from_q.return_value = filter_object
        request = SimpleNamespace(POST={
            'submit_user_list': 'true',
            'base_list': 'first',
            'keys': '',
            'finalsent': 'first',
            'submitform': 'Create list',
        })

        result = get_user_list(
            request,
            {'first': {'list': object(), 'description': 'First list'}})

        self.assertEqual(result, (filter_object, True))
        get_q_for_user.assert_called_once()
        get_filter_from_q.assert_called_once()
