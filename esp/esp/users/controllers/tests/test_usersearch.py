import datetime
import logging
logger = logging.getLogger(__name__)

from django import forms
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import Group
from django.core import mail
from django.conf import settings
from django.test.client import Client

from esp.middleware import ESPError
from esp.program.models import RegistrationProfile, Program
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.tests.util import user_role_setup
from esp.users.forms.user_reg import ValidHostEmailField
from esp.users.models import User, ESPUser, PasswordRecoveryTicket, UserForwarder, StudentInfo, Permission
from django.test import TestCase
import esp.users.views as views
from esp.program.models import Program

import random
import string

#python manage.py test users.controllers.tests.test_usersearch:TestUserSearchController.test_overlap_bug

from esp.users.controllers.usersearch import UserSearchController


class TestUserSearchController(TestCase):
    controller = UserSearchController()
    program = Program.objects.get(id=88)#Splash

    def _get_combination_post_data(self,list_a, list_b):
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
            'checkbox_and_attended':'',
            'csrfmiddlewaretoken': '3kn9b0NY3t6WNbDRqA7zq7dy6FVOF8iD',
            'grade_max': '',
            'student_sendto_self': '1',
            'zipdistance_exclude': '',
        }



    def test_student_confirmed(self):
        post_data = self._get_combination_post_data('Student','confirmed')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)

        self.assertGreater(qobject.count(), 0)


    def test_teacher_classroom_tables(self):
        post_data = self._get_combination_post_data('Teacher','teacher_res_150_8')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertGreater(qobject.count(), 0)

    def test_teacher_classroom_tables_query_from_post(self):
        post_data = {u'username': u'',
                     u'zipdistance_exclude': u'',
                     u'first_name': u'',
                     u'last_name': u'',
                     u'use_checklist': u'0',
                     u'gradyear_max': u'',
                     u'userid': u'',
                     u'school': u'',
                     u'combo_base_list': u'Teacher:teacher_res_150_8',
                     u'zipcode': u'',
                     u'states': u'',
                     u'student_sendto_self': u'1',
                     u'checkbox_and_teacher_res_152_0': u'',
                     u'grade_min': u'',
                     u'gradyear_min': u'',
                     u'zipdistance': u'',
                      u'csrfmiddlewaretoken': u'GKk9biBZE2muppi7jcv2OnqQyIehiCuw',
                      u'grade_max': u'', u'email': u''}

        query =  self.controller.query_from_postdata(self.program, post_data)
        # TODO(benkraft): what is going on here?  Should these tests be getting
        # run?
        logger.info(query) # need to inspect why this is failing
        assert False
        #self.assertGreater(qobject.count(), 0)

    def test_teacher_interview(self):
        post_data = self._get_combination_post_data('Teacher','interview')
        qobject = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertGreater(qobject.count(), 0)
