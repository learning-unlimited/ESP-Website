import unittest

from django.db.models.query import Q

from esp.middleware import ESPError_Log
from esp.users.views.usersearch import add_top_level_filter


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
