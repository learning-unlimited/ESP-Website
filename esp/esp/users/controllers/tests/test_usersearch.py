from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)

from django.db.models.query import Q

from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser
from esp.users.controllers.usersearch import UserSearchController


class TestUserSearchController(ProgramFrameworkTest):

    def setUp(self):
        super(TestUserSearchController, self).setUp()
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
            'combo_base_list': '%s:%s'%(list_a, list_b),
            'email': '',
            'states': '',
            'zipdistance': '',
            'grade_min': '',
            'gradyear_min': '',
            'checkbox_and_attended': '',
            'csrfmiddlewaretoken': '3kn9b0NY3t6WNbDRqA7zq7dy6FVOF8iD',
            'grade_max': '',
            'student_sendto_self': '1',
            'zipdistance_exclude': '',
        }

    def test_student_confirmed(self):
        post_data = self._get_combination_post_data('Student', 'confirmed')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)

        self.assertGreater(qobject.count(), 0)

    def test_teacher_classroom_tables(self):
        post_data = self._get_combination_post_data('Teacher', 'teacher_res_150_8')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertGreater(qobject.count(), 0)

    def test_teacher_classroom_tables_query_from_post(self):
        post_data = {'username': '',
                     'zipdistance_exclude': '',
                     'first_name': '',
                     'last_name': '',
                     'use_checklist': '0',
                     'gradyear_max': '',
                     'userid': '',
                     'school': '',
                     'combo_base_list': 'Teacher:teacher_res_150_8',
                     'zipcode': '',
                     'states': '',
                     'student_sendto_self': '1',
                     'checkbox_and_teacher_res_152_0': '',
                     'grade_min': '',
                     'gradyear_min': '',
                     'zipdistance': '',
                     'csrfmiddlewaretoken': 'GKk9biBZE2muppi7jcv2OnqQyIehiCuw',
                     'grade_max': '', 'email': ''}

        query = self.controller.query_from_postdata(self.program, post_data)
        self.assertIsInstance(query, Q)

    def test_teacher_interview(self):
        post_data = self._get_combination_post_data('Teacher', 'interview')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertGreater(qobject.count(), 0)
