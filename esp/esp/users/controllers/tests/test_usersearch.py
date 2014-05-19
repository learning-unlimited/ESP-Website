import datetime

from model_mommy import mommy

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
from esp.users.views import make_user_admin
from django.test import TestCase
import esp.users.views as views
from esp.program.models import Program

import random
import string
        
#python manage.py test users.controllers.tests.test_usersearch:TestUserSearchController.test_overlap_bug

from esp.users.controllers.usersearch import UserSearchController
class TestUserSearchController(TestCase):


    def test_overlap_bug(self):

        post_data = {
            'username': '',
            'checkbox_and_confirmed': '',
            'first_name': '',
            'last_name': '',
            'school': '',
            'use_checklist': '0',
            'gradyear_max': '',
            'userid': '',
            'zipcode': '',
            'combo_base_list': 'Student:confirmed',
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


        #response = self.client.post('/manage/Spark/2013/selectList',post_data)
        controller = UserSearchController()
        qobject = controller.filter_from_postdata(Program.objects.get(id=88), post_data)

        num_users = ESPUser.objects.filter(qobject.get_Q()).count()   
        print ESPUser.objects.filter(qobject.get_Q()).query
        assert num_users > 0


