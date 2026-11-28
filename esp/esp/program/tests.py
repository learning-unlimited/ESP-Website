from __future__ import absolute_import
from __future__ import division
import six
from six.moves import range
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
import decimal

import logging
logger = logging.getLogger(__name__)

from esp.accounting.models import LineItemType
from esp.cal.models import EventType, Event
from esp.program.models import Program, ClassSection, RegistrationProfile, ScheduleMap, ProgramModule, StudentRegistration, RegistrationType, ClassCategories, ClassSubject, BooleanExpression, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ScheduleTestSectionList
from esp.qsd.models import QuasiStaticData
from esp.resources.models import Resource, ResourceRequest, ResourceType
from esp.users.models import ESPUser, ContactInfo, StudentInfo, TeacherInfo, Permission, Record, RecordType
from esp.web.models import NavBarCategory
from esp.tagdict.models import Tag

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.test import LiveServerTestCase, TransactionTestCase, override_settings
from django.utils import timezone
import unittest
from unittest import mock
from django.test.client import Client
from django import forms

from esp.program.controllers.classreg import get_custom_fields
from esp.program.controllers.lottery.base import LotteryException
from esp.program.controllers.lottery import ilp as ilp_lottery
from esp.program.controllers.lottery.base import BaseLotteryAssignmentController
from esp.program.controllers.lottery.ilp import ILPLotteryAssignmentController
from esp.program.controllers.lottery.legacy import LegacyLotteryAssignmentController
from esp.program.controllers.lottery.refresh import (
    TERMINAL_STATUSES, refresh_run_from_service, resolve_solver_client, resolve_solver_client_by_name,
)
from esp.program.controllers.lottery.remote import RemoteSolverClient, RemoteSolverError
from esp.program.models import LotteryInputSnapshot, LotteryRun
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.forms import ProgramCreationForm
from esp.program.modules.base import ProgramModuleObj
from esp.program.setup import prepare_program, commit_program
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup

from datetime import datetime, timedelta
from decimal import Decimal
import csv
import hashlib
import json
import numpy
import random
import re
import requests
import socket
import tempfile
import threading
import time
import unicodedata

class ViewUserInfoTest(TestCase):
    def setUp(self):

        """ Set up a bunch of user accounts to play with """
        self.password = "pass1234"

        #   May fail once in a while, but it's not critical.
        self.unique_name = 'Test_UNIQUE%06d' % random.randint(0, 999999)
        self.user, created = ESPUser.objects.get_or_create(first_name=self.unique_name, last_name="User", username="testuser123543", email="server@esp.mit.edu")
        if created:
            self.user.set_password(self.password)
            self.user.save()

        self.admin, created = ESPUser.objects.get_or_create(first_name="Admin", last_name="User", username="adminuser124353", email="server@esp.mit.edu")
        if created:
            self.admin.set_password(self.password)
            self.admin.save()

        self.fake_admin, created = ESPUser.objects.get_or_create(first_name="Not An Admin", last_name="User", username="notanadminuser124353", email="server@esp.mit.edu")
        if created:
            self.fake_admin.set_password(self.password)
            self.fake_admin.save()

        self.admin.makeRole('Administrator')


    def assertStringContains(self, string, contents):
        if not (contents in string):
            self.assert_(False, "'%s' not in '%s'" % (contents, string))

    def assertNotStringContains(self, string, contents):
        if contents in string:
            self.assert_(False, "'%s' are in '%s' and shouldn't be" % (contents, string))

    def testIssue1448UsernameMatchesFirstName(self):
        """
        Test for issue: https://github.com/learning-unlimited/ESP-Website/issues/1448

        If someone creates an account with a username that is also someone else's first name or last name,
        then you can't search by that first name or last name in the admin toolbar, because you'll just be
        taken to the first account rather than the search page with the list of accounts having that name.

        This was probably considered a feature at one point. But right now it's more of a bug.
        If we really want to maintain some functionality for exact matching, maybe the results page can be
        organized so that, when there's an exact match, it says something like: "found user with username "foo",
        also found other matching users" followed by the current results page. And if there is nothing but the exact
        match, then we can have the current behavior of redirecting directly to that profile.

        Steps to reproduce:

        Create account 1 with a username abcabc.
        Create account 2 with a different username, but first name abcabc.
        Now from an admin account, search for abcabc in the admin toolbar.
        You get taken to account 1, but you might have wanted account 2.
        """
        username = 'abcabc'
        self.user.username = username
        self.user.save()

        self.admin.first_name = username
        self.admin.save()

        c = Client()
        c.login(username=self.admin.username, password=self.password)

        # Try searching by ID
        response = c.get("/manage/usersearch", { "userstr": username })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), 'Multiple users matched the criteria that you specified')


    def testUserIDSearchOneResult(self):
        c = Client()
        c.login(username=self.admin.username, password=self.password)

        # Try searching by ID direct hit
        response = c.get("/manage/usersearch", { "userstr": str(self.admin.id) })
        self.assertStringContains(response['location'], "/manage/userview?username=adminuser124353")


    def testUserIDSearchMultipleResults(self):
        c = Client()
        c.login(username=self.admin.username, password=self.password)
        self.user.username = str(self.admin.id)
        self.user.save()

        # Try searching by ID direct hit
        response = c.get("/manage/usersearch", { "userstr": self.admin.id })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), 'Multiple users matched the criteria that you specified')


    def testUserSearchFn(self):
        """
        Tests whether the user-search page works properly.
        Note that this doubles as a test of the find_user function,
        because this page is a very lightweight wrapper around that function.
        """
        c = Client()
        c.login(username=self.admin.username, password=self.password)

        # Try searching by username
        response = c.get("/manage/usersearch", { "userstr": str(self.fake_admin.username) })
        self.assertEqual(response.status_code, 302)
        self.assertStringContains(response['location'], "/manage/userview?username=notanadminuser124353")

        # Try some fuzzy searches
        # First name only, unique
        response = c.get("/manage/usersearch", { "userstr": self.unique_name })
        self.assertEqual(response.status_code, 302)
        self.assertStringContains(response['location'], "/manage/userview?username=testuser123543")

        # Full name, unique

        # I don't think this makes any sense, surely there is more than one

        # response = c.get("/manage/usersearch", { "userstr": "Admin User" })
        # self.assertEqual(response.status_code, 302)
        # self.assertStringContains(response['location'], "/manage/userview?username=adminuser124353")

        # Last name, not unique
        response = c.get("/manage/usersearch", { "userstr": "User" })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.admin.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.fake_admin.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.user.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), 'href="/manage/userview?username=adminuser124353"')

        # Partial first name, not unique
        response = c.get("/manage/usersearch", { "userstr": "Adm" })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.admin.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.fake_admin.username)
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), self.user.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), 'href="/manage/userview?username=adminuser124353"')

        # Partial first name and last name, not unique
        response = c.get("/manage/usersearch", { "userstr": "Adm User" })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.admin.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), self.fake_admin.username)
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), self.user.username)
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), 'href="/manage/userview?username=adminuser124353"')

        # Now, make sure we properly do nothing when there're no users to do anything to
        response = c.get("/manage/usersearch", { "userstr": "NotAUser9283490238" })
        self.assertStringContains(six.text_type(response.content, encoding='UTF-8'), "No user found by that name!")
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), self.admin.username)
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), self.fake_admin.username)
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), self.user.username)
        self.assertNotStringContains(six.text_type(response.content, encoding='UTF-8'), 'href="/manage/userview?username=adminuser124353"')


    def testUserInfoPage(self):
        """ Tests the /manage/userview view, that displays information about arbitrary users to admins """
        c = Client()
        self.assertTrue( c.login(username=self.admin.username, password=self.password), "Couldn't log in as admin" )

        # Test to make sure we can get a user's page
        # (I'm just going to assume that the template renders properly;
        # too lame to do a real thorough test of it...)
        response = c.get("/manage/userview", { 'username': self.user.username })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].id, self.user.id)
        self.assert_(self.user.username in six.text_type(response.content, encoding='UTF-8'))
        self.assert_(self.user.first_name in six.text_type(response.content, encoding='UTF-8'))
        self.assert_(self.user.last_name in six.text_type(response.content, encoding='UTF-8'))
        self.assert_(str(self.user.id) in six.text_type(response.content, encoding='UTF-8'))

        # Test to make sure we get an error on an unknown user
        response = c.get("/manage/userview", { 'username': "NotARealUser" })
        self.assertEqual(response.status_code, 500)

        # Now, make sure that only admins can view this page
        self.assertTrue( c.login(username=self.fake_admin.username, password=self.password), "Couldn't log in as fake admin" )
        response = c.get("/manage/userview", { 'username': self.user.username })
        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        self.user.delete()
        self.admin.delete()
        self.fake_admin.delete()



class ProfileTest(TestCase):

    def setUp(self):
        self.salt = hashlib.sha1(str(random.random()).encode("UTF-8")).hexdigest()[:5]

    def testAcctCreate(self):
        self.u=ESPUser.objects.create_user(
            first_name='bob',
            last_name='jones',
            username='bjones',
            email='test@bjones.com',
            # is_staff=True,
        )
        self.u.set_password('123!@#')
        self.u.save()
        self.group=Group(name='Test Group')
        self.group.save()
        self.u.groups.add(self.group)
        self.assertEquals(ESPUser.objects.get(username='bjones'), self.u)
        self.assertEquals(Group.objects.get(name='Test Group'), self.group)


class ProgramHappenTest(TestCase):
    """
    Make a program happen!
    This test case runs through a bunch of essential pages.
    It mostly just makes sure they don't error out.
    """

    def loginAdmin(self):
        self.assertEqual( self.client.login(username='ubbadmubbin', password='pubbasswubbord'), True, six.u('Oops, login failed!') )
    def loginTeacher(self):
        self.assertEqual( self.client.login(username='tubbeachubber', password='pubbasswubbord'), True, six.u('Oops, login failed!') )
    def loginStudent(self):
        self.assertEqual( self.client.login(username='stubbudubbent', password='pubbasswubbord'), True, six.u('Oops, login failed!') )

    def setUp(self):
        #create Groups for userroles
        user_role_setup()

        def makeuser(f, l, un, email, p):
            u = ESPUser.objects.create_user(first_name=f, last_name=l, username=un, email=email)
            u.set_password(p)
            u.save()
            return u

        # make people -- presumably we're testing actual account creation elsewhere
        self.admin = makeuser('Ubbad', 'Mubbin', 'ubbadmubbin', 'ubbadmubbin@esp.mit.edu', 'pubbasswubbord')
        self.student = makeuser('Stubbu', 'Dubbent', 'stubbudubbent', 'stubbudubbent@esp.mit.edu', 'pubbasswubbord')
        self.teacher = makeuser('Tubbea', 'Chubber', 'tubbeachubber', 'tubbeachubber@esp.mit.edu', 'pubbasswubbord')

        self.admin.makeRole("Administrator")
        self.student.makeRole("Student")
        self.teacher.makeRole("Teacher")

    def makeprogram(self):
        """ Test program creation through the web form. """
        # Make stuff that a program needs
        ClassCategories.objects.create(symbol='X', category='Everything')
        ClassCategories.objects.create(symbol='N', category='Nothing')
        ProgramModule.objects.create(link_title='Default Module', admin_title='Default Module (do stuff)', module_type='learn', handler='StudentRegCore', seq=0, required=False)
        ProgramModule.objects.create(link_title='Register Your Classes', admin_title='Teacher Class Registration', module_type='teach', handler='TeacherClassRegModule',
            inline_template='listclasses.html', seq=10, required=False)
        ProgramModule.objects.create(link_title='Sign up for Classes', admin_title='Student Class Registration', module_type='learn', handler='StudentClassRegModule',
            seq=10, required=True)
        ProgramModule.objects.create(link_title='Sign up for a Program', admin_title='Student Registration Core', module_type='learn', handler='StudentRegCore',
            seq=-9999, required=False)

        # Admin logs in
        self.loginAdmin()
        # Admin prepares program
        prog_dict = {
                'term': '3001_Winter',
                'term_friendly': 'Winter 3001',
                'grade_min': '7',
                'grade_max': '12',
                'director_email': 'esp@mit.edu',
                'program_size_max': '3000',
                'program_type': 'Prubbogrubbam!',
                'program_modules': [x.id for x in ProgramModule.objects.all()],
                'class_categories': [x.id for x in ClassCategories.objects.all()],
                'admins': self.admin.id,
                'teacher_reg_start': '2000-01-01 00:00:00',
                'teacher_reg_end':   '3001-01-01 00:00:00',
                'student_reg_start': '2000-01-01 00:00:00',
                'student_reg_end':   '3001-01-01 00:00:00',
                'publish_start':     '2000-01-01 00:00:00',
                'publish_end':       '3001-01-01 00:00:00',
                'base_cost':         '666',
            }
        self.client.post('/manage/newprogram', prog_dict)
        self.client.post('/manage/newprogram?checked=1', {})

        # Now test correctness...
        self.prog = Program.by_prog_inst('Prubbogrubbam', prog_dict['term'])
        # Name
        self.assertEqual( self.prog.niceName(), six.u('Prubbogrubbam! Winter 3001'), six.u('Program creation failed.') )
        # Options
        self.assertEqual(
            [six.text_type(x) for x in
                [self.prog.grade_min,         self.prog.grade_max,
                 self.prog.director_email,    self.prog.program_size_max] ],
            [six.text_type(x) for x in
                [prog_dict['grade_min'],      prog_dict['grade_max'],
                 prog_dict['director_email'], prog_dict['program_size_max']] ],
            six.u('Program options not properly set.') )
        # Program Cost
        self.assertEqual(
            Decimal(LineItemType.objects.get(required=True, program=self.prog).amount),
            Decimal(prog_dict['base_cost']),
            'Program admission cost not set properly.' )

    def teacherreg(self):
        """ Test teacher registration (currently just class reg) through the web form. """

        # Just register a class for now.
        # Make rooms & times, since I'm too lazy to do that as a test just yet.

        self.assertTrue( self.prog.classes().count() == 0, 'Website thinks empty program has classes')
        user_obj = ESPUser.objects.get(username='tubbeachubber')
        self.assertTrue( user_obj.getTaughtClasses().count() == 0, "User tubbeachubber is teaching classes that don't exist")
        self.assertTrue( user_obj.getTaughtSections().count() == 0, "User tubbeachubber is teaching sections that don't exist")

        timeslot_type = EventType.get_from_desc('Class Time Block')
        now = datetime.now()
        self.timeslot = Event.objects.create(program=self.prog, description='Now', short_description='Right now',
            start=now, end=now+timedelta(0, 3600), event_type=timeslot_type )

        # Make some other time slots
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0, 3600), end=now+timedelta(0, 2*3600), event_type=timeslot_type )
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0, 2*3600), end=now+timedelta(0, 3*3600), event_type=timeslot_type )
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0, 3*3600), end=now+timedelta(0, 4*3600), event_type=timeslot_type )

        classroom_type = ResourceType.objects.create(name='Classroom', consumable=False, priority_default=0,
            description='Each classroom or location is a resource; almost all classes need one.')
        self.classroom = Resource.objects.create(name='Nowhere', num_students=50, res_type=classroom_type, event=self.timeslot)

        # Teacher logs in and posts class
        self.loginTeacher()
        num_sections = 3
        class_dict = {
            'title': 'Chairing',
            'category': self.prog.class_categories.all()[0].id,
            'class_info': 'Chairing is fun!',
            'prereqs': 'A chair.',
            'duration': self.prog.getDurations()[0][0],
            'num_sections': str(num_sections),
            'session_count': '1',
            'grade_min': self.prog.grade_min,
            'grade_max': self.prog.grade_max,
            'class_size_max': '10',
            'allow_lateness': 'False',
            'message_for_directors': 'Hi chairs!',
            'class_reg_page': '1',
            'hardness_rating': '**',
            #   Additional keys to test resource forms:
            'request-TOTAL_FORMS': '2',
            'request-INITIAL_FORMS': '2',
            'request-MAX_NUM_FORMS': '1000',
            'request-0-resource_type': str(ResourceType.get_or_create('Classroom').id),
            'request-0-desired_value': 'Lecture',
            'request-1-resource_type': str(ResourceType.get_or_create('A/V').id),
            'request-1-desired_value': 'LCD projector',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
        }

        #   Fill in required fields from any custom forms used by the program
        #   This should be improved in the future (especially if we have dynamic forms)
        custom_fields_dict = get_custom_fields()
        for field in custom_fields_dict:
            if isinstance(custom_fields_dict[field], forms.ChoiceField):
                class_dict[field] = custom_fields_dict[field].choices[0][0]
            else:
                class_dict[field] = 'foo'

        # Check that stuff went through correctly
        response = self.client.post('%smakeaclass' % self.prog.get_teach_url(), class_dict)

        # check prog.classes
        classes = self.prog.classes()
        self.assertEqual( classes.count(), 1, 'Classes failing to show up in program' )
        self.classsubject = classes[0]

        # check the title ise good
        self.assertEqual( six.text_type(self.classsubject.title), six.text_type(class_dict['title']), 'Failed to save title.' )

        # check getTaughtClasses
        getTaughtClasses = user_obj.getTaughtClasses()
        self.assertEqual( getTaughtClasses.count(), 1, "User's getTaughtClasses is the wrong size" )
        self.assertEqual( getTaughtClasses[0], self.classsubject, "User's getTaughtClasses is wrong" )
        # repeat with program-specific one
        getTaughtClasses = user_obj.getTaughtClasses()
        self.assertEqual( getTaughtClasses.count(), 1, "User's getTaughtClasses is the wrong size" )
        self.assertEqual( getTaughtClasses[0], self.classsubject, "User's getTaughtClasses is wrong" )

        # check getTaughtSections
        getTaughtSections = user_obj.getTaughtSections()
        self.assertEqual( getTaughtSections.count(), num_sections, "User tubbeachubber is not teaching the right number of sections" )
        for section in getTaughtSections:
            self.assertEqual( section.parent_class, self.classsubject, "Created section has incorrect parent_class." )
        # repeat with program-specific one
        getTaughtSections = user_obj.getTaughtSections(program=self.prog)
        self.assertEqual( getTaughtSections.count(), num_sections, "User tubbeachubber is not teaching the right number of sections" )
        for section in getTaughtSections:
            self.assertEqual( section.parent_class, self.classsubject, "Created section has incorrect parent_class." )

    def studentreg(self):
        # Check that you're in no classes
        self.assertEqual( self.student.getEnrolledClasses().count(), 0, "Student incorrectly enrolled in a class" )
        self.assertEqual( self.student.getEnrolledSections().count(), 0, "Student incorrectly enrolled in a section")

        # Approve and schedule a class, because I'm too lazy to have this run as a test just yet.
        self.classsubject.accept()
        sec = self.classsubject.sections.all()[0]
        sec.meeting_times.add(self.timeslot)
        sec.assignClassRoom(self.classroom)

        # shortcut student profile creation -- presumably we're also testing this elsewhere
        thisyear = ESPUser.program_schoolyear(self.prog)
        prof = RegistrationProfile.getLastForProgram(self.student, self.prog)
        prof.contact_user = ContactInfo.objects.create( user=self.student, first_name=self.student.first_name, last_name=self.student.last_name, e_mail=self.student.email )
        prof.student_info = StudentInfo.objects.create( user=self.student, graduation_year=ESPUser.YOGFromGrade(10, ESPUser.program_schoolyear(self.prog)), dob=datetime(thisyear-15, 1, 1) )
        prof.save()

        # Student logs in and signs up for classes
        self.loginStudent()
        response = self.client.get('%sstudentreg' % self.prog.get_learn_url())
        reg_dict = {
            'class_id': self.classsubject.id,
            'section_id': sec.id,
        }

        # Try signing up for a class.
        self.client.post('%saddclass' % self.prog.get_learn_url(), reg_dict)

        sr = StudentRegistration.objects.all()[0]

        enrolled = RegistrationType.get_cached(name='Enrolled',
                                               category='student')
        self.assertTrue( StudentRegistration.valid_objects().filter(user=self.student, section=sec,
            relationship=enrolled).count() > 0, 'Registration failed.')

        # Check that you're in it now
        self.assertEqual( self.student.getEnrolledClasses().count(), 1, "Student not enrolled in exactly one class" )
        self.assertEqual( self.student.getEnrolledSections().count(), 1, "Student not enrolled in exactly one section" )

        # Try dropping a class.
        self.client.get('%sclearslot/%s' % (self.prog.get_learn_url(), self.timeslot.id))
        self.assertFalse( StudentRegistration.valid_objects().filter(user=self.student, section=sec,
            relationship=enrolled).count() > 0, 'Registration failed.')

        # Check that you're in no classes
        self.assertEqual( self.student.getEnrolledClasses().count(), 0, "Student incorrectly enrolled in a class" )
        self.assertEqual( self.student.getEnrolledSections().count(), 0, "Student incorrectly enrolled in a section")

    def runTest(self):
        self.makeprogram()
        self.teacherreg()
        self.studentreg()

class ProgramFrameworkTest(TestCase):
    """ A test case that initializes a program with the parameters passed to setUp().
        Everything is done with get_or_create so it can be run multiple times in the
        same session.

        This is intended to facilitate the writing of unit tests for program modules
        and other functions that deal with program-specific data.  Once the setUp()
        function is called, you can use self.students, self.teachers, self.program
        and the settings.
    """

    def setUp(self, *args, **kwargs):
        # We manually cache the creation of resource types
        # since the cache persists between tests, and the underlying database objects do not
        # we clear it here
        ResourceType._get_or_create_cache = {}

        user_role_setup()

        #   Default parameters
        settings = {'num_timeslots': 3,
                    'timeslot_length': 50,
                    'timeslot_gap': 10,
                    'room_capacity': 30,
                    'num_categories': 2,
                    'num_rooms': 4,
                    'num_teachers': 5,
                    'classes_per_teacher': 2,
                    'sections_per_class': 1,
                    'num_students': 10,
                    'num_admins': 1,
                    'modules': ProgramModule.objects.all(),
                    'program_type': 'TestProgram',
                    'program_instance_name': '2222_Summer',
                    'program_instance_label': 'Summer 2222',
                    'start_time': datetime(2222, 7, 7, 7, 5),
                    'base_cost': 666,
                    'sibling_discount': 0
                    }

        #   Override parameters explicitly
        for key in settings:
            if key in kwargs:
                settings[key] = kwargs[key]

        self.settings = settings

        #   Create class categories
        self.categories = []
        for i in range(settings['num_categories']):
            cat, created = ClassCategories.objects.get_or_create(category='Category %d' % i, symbol=chr(65+i))
            self.categories.append(cat)

        #   Create users
        self.teachers = []
        self.students = []
        self.admins = []
        for i in range(settings['num_students']):
            name = six.u('student%04d') % i
            new_student, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+six.u('@learningu.org'))
            new_student.set_password('password')
            new_student.save()
            new_student.makeRole("Student")
            self.students.append(new_student)
        for i in range(settings['num_teachers']):
            name = six.u('teacher%04d') % i
            new_teacher, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+six.u('@learningu.org'))
            new_teacher.set_password('password')
            new_teacher.save()
            new_teacher.makeRole("Teacher")
            self.teachers.append(new_teacher)
        for i in range(settings['num_admins']):
            name = six.u('admin%04d') % i
            new_admin, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+six.u('@learningu.org'))
            new_admin.set_password('password')
            new_admin.save()
            new_admin.makeRole("Administrator")
            self.admins.append(new_admin)

        #   Establish attributes for program
        prog_form_values = {
                'term': settings['program_instance_name'],
                'term_friendly': settings['program_instance_label'],
                'grade_min': '7',
                'grade_max': '12',
                'director_email': 'esp@mit.edu',
                'program_size_max': '3000',
                'program_type': settings['program_type'],
                'program_modules': settings['modules'],
                'class_categories': [x.id for x in self.categories],
                'admins': [x.id for x in self.admins],
                'teacher_reg_start': '2000-01-01 00:00:00',
                'teacher_reg_end':   '3001-01-01 00:00:00',
                'student_reg_start': '2000-01-01 00:00:00',
                'student_reg_end':   '3001-01-01 00:00:00',
                'base_cost':         settings['base_cost'],
                'sibling_discount':  settings['sibling_discount'],
            }

        #   Create the program much like the /manage/newprogram view does
        pcf = ProgramCreationForm(prog_form_values)
        if not pcf.is_valid():
            logger.info("ProgramCreationForm errors")
            logger.info(pcf.data)
            logger.info(pcf.errors)
            logger.info(prog_form_values)
            raise Exception("Program form creation errors")

        temp_prog = pcf.save(commit=False)
        (perms, modules) = prepare_program(temp_prog, pcf.data)

        new_prog = pcf.save(commit=False) # don't save, we need to fix it up:

        #   Filter out unwanted characters from program type to form URL
        ptype_slug = re.sub(r'[-\s]+', '_', re.sub(r'[^\w\s-]', '', unicodedata.normalize('NFKD', pcf.cleaned_data['program_type'])).strip())
        new_prog.url = ptype_slug + "/" + pcf.cleaned_data['term']
        new_prog.name = pcf.cleaned_data['program_type'] + " " + pcf.cleaned_data['term_friendly']
        new_prog.save()
        pcf.save_m2m()

        commit_program(new_prog, perms, pcf.cleaned_data['base_cost'], pcf.cleaned_data['sibling_discount'])

        #   Add recursive permissions to open registration to the appropriate people
        (perm, created) = Permission.objects.get_or_create(role=Group.objects.get(name='Teacher'), permission_type='Teacher/All', program=new_prog)
        (perm, created) = Permission.objects.get_or_create(role=Group.objects.get(name='Student'), permission_type='Student/All', program=new_prog)

        self.program = new_prog

        #   Create timeblocks and resources
        self.event_type = EventType.get_from_desc('Class Time Block')
        for i in range(settings['num_timeslots']):
            start_time = settings['start_time'] + timedelta(minutes=i * (settings['timeslot_length'] + settings['timeslot_gap']))
            end_time = start_time + timedelta(minutes=settings['timeslot_length'])
            event, created = Event.objects.get_or_create(program=self.program, event_type=self.event_type, start=start_time, end=end_time, short_description='Slot %i' % i, description=start_time.strftime("%H:%M %m/%d/%Y"))
        self.timeslots = self.program.getTimeSlots()
        for i in range(settings['num_rooms']):
            for ts in self.timeslots:
                res, created = Resource.objects.get_or_create(name='Room %d' % i, num_students=settings['room_capacity'], event=ts, res_type=ResourceType.get_or_create('Classroom'))
        self.rooms = self.program.getClassrooms()

        #   Create classes and sections
        subject_count = 0
        for t in self.teachers:
            for i in range(settings['classes_per_teacher']):
                current_category = self.categories[subject_count % settings['num_categories']]
                new_class, created = ClassSubject.objects.get_or_create(title='Test class %d' % subject_count, category=current_category, grade_min=7, grade_max=12, parent_program=self.program, class_size_max=settings['room_capacity'], class_info='Description %d!' % subject_count)
                new_class.makeTeacher(t)
                subject_count += 1
                for j in range(settings['sections_per_class']):
                    if new_class.get_sections().count() <= j:
                        new_class.add_section(duration=settings['timeslot_length']/60.0)
                new_class.accept()

        #   Give the program its own QSD main-page
        (qsd, created) = QuasiStaticData.objects.get_or_create(url='learn/%s/index' % self.program.url,
                                              name="learn:index",
                                              title=new_prog.niceName(),
                                              content="Welcome to %s!  Click <a href='studentreg'>here</a> to go to Student Registration.  Click <a href='catalog'>here</a> to view the course catalog.",
                                              author=self.admins[0],
                                              nav_category=NavBarCategory.objects.get_or_create(name="learn", long_explanation="", include_auto_links=False)[0])

    #   Helper function to give the program a schedule.
    #   Does not get called by default, but subclasses can call it.
    def schedule_randomly(self):
        #   Clear scheduled classes to get a clean schedule
        for cls in self.program.classes():
            for sec in cls.get_sections():
                sec.clearRooms()
                sec.clear_meeting_times()
        #   Force availability
        for t in self.teachers:
            for ts in self.program.getTimeSlots():
                t.addAvailableTime(self.program, ts)
        for cls in self.program.classes():
            for sec in cls.get_sections():
                vt = sec.viable_times()
                if len(vt) > 0:
                    sec.assign_start_time(random.choice(vt))
                    vr = sec.viable_rooms()
                    if len(vr) > 0:
                        sec.assign_room(random.choice(vr))

    def add_user_profiles(self):
        """Helper function to give each user a profile so they can register.

        Does not get called by default, but subclasses can call it.
        """
        for student in self.students:
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.program_schoolyear(self.program)+2)
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, program=self.program, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()
        for teacher in self.teachers:
            teacher_teacherinfo = TeacherInfo(user=teacher)
            teacher_teacherinfo.save()
            digit = teacher.id % 10
            phone = (six.u('%d') % digit) * 10
            teacher_contactinfo = ContactInfo(
                user=teacher,
                first_name=teacher.first_name,
                last_name=teacher.last_name,
                e_mail=teacher.email,
                phone_day=phone,
                phone_cell=phone,
            )
            teacher_contactinfo.save()
            teacher_regprofile = RegistrationProfile(
                user=teacher,
                program=self.program,
                teacher_info=teacher_teacherinfo,
                contact_user=teacher_contactinfo,
                most_recent_profile=True,
            )
            teacher_regprofile.save()

    # For backwards compatability.
    add_student_profiles = add_user_profiles

    #   Helper function to put the students in classes.
    #   Does not get called by default, but subclasses can call it.
    def classreg_students(self):
        ignore_ts = []
        for student in self.students:
            schedule_full = False
            while not schedule_full:
                sm = ScheduleMap(student, self.program)
                empty_slots = [x for x in list(sm.map.keys()) if x not in ignore_ts and len(sm.map[x]) == 0]
                if len(empty_slots) == 0:
                    schedule_full = True
                    break
                target_ts = random.choice(empty_slots)
                if self.program.sections().filter(meeting_times=target_ts).exists():
                    sec = random.choice(self.program.sections().filter(meeting_times=target_ts))
                    sec.preregister_student(student, fast_force_create=True)
                else:
                    ignore_ts.append(target_ts)

    # Helper function to create another program in the past
    # Does not get called by default, but subclasses can call it
    def create_past_program(self):
        # Make a program
        prog_form_values = {
                'term': '1901_Spring',
                'term_friendly': 'Spring 1901',
                'grade_min': '7',
                'grade_max': '12',
                'director_email': 'esp@mit.edu',
                'program_size_max': '3000',
                'program_type': 'TestProgramPast',
                'program_modules': [x.id for x in ProgramModule.objects.all()],
                'class_categories': [x.id for x in self.categories],
                'admins': [x.id for x in self.admins],
                'teacher_reg_start': '1901-01-01 00:00:00',
                'teacher_reg_end':   '2000-01-01 00:00:00',
                'student_reg_start': '1901-01-01 00:00:00',
                'student_reg_end':   '2000-01-01 00:00:00',
                'base_cost':         '666',
                'finaid_cost':       '37',
            }
        pcf = ProgramCreationForm(prog_form_values)
        if not pcf.is_valid():
            logger.info("ProgramCreationForm errors")
            logger.info(pcf.data)
            logger.info(pcf.errors)
            logger.info(prog_form_values)
            raise Exception('Problem creating a past program')

        temp_prog = pcf.save(commit=False)
        (perms, modules) = prepare_program(temp_prog, pcf.cleaned_data)

        new_prog = pcf.save(commit=False) # don't save, we need to fix it up:

        #   Filter out unwanted characters from program type to form URL
        ptype_slug = re.sub(r'[-\s]+', '_', re.sub(r'[^\w\s-]', '', unicodedata.normalize('NFKD', pcf.cleaned_data['program_type'])).strip())
        new_prog.url = ptype_slug + "/" + pcf.cleaned_data['term']
        new_prog.name = pcf.cleaned_data['program_type'] + " " + pcf.cleaned_data['term_friendly']
        new_prog.save()
        pcf.save_m2m()

        commit_program(new_prog, perms, pcf.cleaned_data['base_cost'])

        self.new_prog = new_prog

        #   Default parameters
        past_settings = {'num_timeslots': 3,
                    'timeslot_length': 50,
                    'timeslot_gap': 10,
                    'start_time': datetime(1901, 7, 7, 7, 5),
                    }

        #   Create timeblocks
        event_type = EventType.get_from_desc('Class Time Block')
        for i in range(past_settings['num_timeslots']):
            start_time = past_settings['start_time'] + timedelta(minutes=i * (past_settings['timeslot_length'] + past_settings['timeslot_gap']))
            end_time = start_time + timedelta(minutes=past_settings['timeslot_length'])
            event, created = Event.objects.get_or_create(program=self.new_prog, event_type=event_type, start=start_time, end=end_time, short_description='Slot %i' % i, description=start_time.strftime("%H:%M %m/%d/%Y"))


class ProgramCapTest(ProgramFrameworkTest):
    """Test various forms of program cap."""
    def setUp(self):
        super(ProgramCapTest, self).setUp(num_students=20)
        self.schedule_randomly()
        # The students it creates will be in 10th grade.
        self.add_user_profiles()

        self.tenth_graders = self.students[:-10]
        # Make some be in 11th grade
        self.eleventh_graders = self.students[-10:-5]
        for student in self.eleventh_graders:
            student.set_grade(student.getGrade() + 1)
        # Make some be in 9th grade
        self.ninth_graders = self.students[-5:]
        for student in self.ninth_graders:
            student.set_grade(student.getGrade() - 1)

    def test_cap_0(self):
        self.program.program_size_max = 0
        self.program.save()
        for user in self.students:
            # Assert that everyone can join the program.
            self.assertTrue(self.program.user_can_join(user))

    def test_cap_none(self):
        self.program.program_size_max = None
        self.program.save()
        for user in self.students:
            # Assert that everyone can join the program.
            self.assertTrue(self.program.user_can_join(user))

    def test_simple_cap(self):
        enrolled, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', category='student')
        self.program.program_size_max = 3
        self.program.save()
        for user in self.students[:3]:
            # Assert that the first 3 users can join.
            self.assertTrue(self.program.user_can_join(user))
            # Join the program!
            StudentRegistration.objects.create(
                user=user, section=self.program.sections()[0],
                relationship=enrolled)
        for user in self.students[3:]:
            # Assert that no more users may join, no matter their grade.
            self.assertFalse(self.program.user_can_join(user))
        for user in self.students[:3]:
            # Assert that the first 3 users can still register (because they're
            # already in the program)
            self.assertTrue(self.program.user_can_join(user))
        # Clean up
        StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program).delete()

    def test_grade_based_cap(self):
        enrolled, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', category='student')
        Tag.objects.create(key='program_size_by_grade',
                           value='{"10": 5, "11-12": 2}',
                           target=self.program)

        for user in self.tenth_graders[:5]:
            # Assert that the first 5 10th graders can join.
            self.assertTrue(self.program.user_can_join(user))
            # Join the program!
            StudentRegistration.objects.create(
                user=user, section=self.program.sections()[0],
                relationship=enrolled)
        for user in self.tenth_graders[5:]:
            # Assert that no more 10th graders may join.
            self.assertFalse(self.program.user_can_join(user))

        for user in self.eleventh_graders[:2]:
            # Assert that the first 2 11th graders can join.
            self.assertTrue(self.program.user_can_join(user))
            # Join the program!
            StudentRegistration.objects.create(
                user=user, section=self.program.sections()[0],
                relationship=enrolled)
        for user in self.eleventh_graders[2:]:
            # Assert that no more 11th graders may join.
            self.assertFalse(self.program.user_can_join(user))
        for user in self.eleventh_graders[:2]:
            # Assert that students who have already registered can still join.
            self.assertTrue(self.program.user_can_join(user))

        for user in self.ninth_graders:
            # Assert that any number of 9th graders can join.
            self.assertTrue(self.program.user_can_join(user))
            # Join the program!
            StudentRegistration.objects.create(
                user=user, section=self.program.sections()[0],
                relationship=enrolled)

        # Clean up
        StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program).delete()
        Tag.objects.filter(key='program_size_by_grade').delete()


def randomized_attrs(program):
    section_list = list(program.sections())
    random.shuffle(section_list)
    timeslot_list = list(program.getTimeSlots())
    random.shuffle(timeslot_list)
    return (section_list, timeslot_list)

class ScheduleMapTest(ProgramFrameworkTest):
    """ Fiddle around with a student's schedule and ensure the changes are
        properly reflected in their schedule map.
    """
    def runTest(self):
        def occupied_slots(smap):
            result = []
            for key in smap:
                if len(smap[key]) > 0:
                    result.append(key)
            return result

        #   Initialize
        student = self.students[0]
        program = self.program
        (section_list, timeslot_list) = randomized_attrs(program)
        section1 = section_list[0]
        section2 = section_list[1]
        ts1 = timeslot_list[0]
        ts2 = timeslot_list[1]
        modules = program.getModules()
        scrmi = program.studentclassregmoduleinfo

        #   Check that the map starts out empty
        sm = ScheduleMap(student, program)
        self.assertTrue(len(occupied_slots(sm.map)) == 0, 'Initial schedule map not empty.')

        #   Put the student in a class and check that it's there
        section1.assign_start_time(ts1)
        section1.preregister_student(student)

        section1 = ClassSection.objects.get(id=section1.id)  ## Go get the class (and its size) again
        self.assertEqual(section1.num_students(), 1, "Cache error, didn't correctly update the number of students in the class")
        self.assertEqual(section1.num_students(), ClassSection.objects.get(id=section1.id).enrolled_students, "Triggers error, didn't update enrolled_students with the new enrollee")
        sm = ScheduleMap(student, program)

        self.assertTrue(occupied_slots(sm.map) == [ts1.id], 'Schedule map is not occupied at (only) the specified ' +
                'timeslot ({}). Occupied slot(s) is/are {}'.format(ts1.id, occupied_slots(sm.map)))
        self.assertTrue(sm.map[ts1.id] == [section1], 'Schedule map contains incorrect value at specified timeslot.')

        #   Reschedule the section and check
        section1.assign_start_time(ts2)
        sm = ScheduleMap(student, program)
        self.assertTrue(occupied_slots(sm.map) == [ts2.id], 'Schedule map incorrectly handled rescheduled section.')
        self.assertTrue(sm.map[ts2.id] == [section1], 'Schedule map contains incorrect section in rescheduled timeslot.')

        #   Double-book the student and make sure both classes show up
        section2.assign_start_time(ts2)
        section2.preregister_student(student)
        sm = ScheduleMap(student, program)
        self.assertTrue(occupied_slots(sm.map) == [ts2.id], 'Schedule map did not identify double-booked timeslot.')
        self.assertTrue(set(sm.map[ts2.id]) == {section1, section2}, 'Schedule map contains incorrect sections in double-booked timeslot.')

        #   Remove the student and check that the map is empty again
        section1.unpreregister_student(student)
        section2.unpreregister_student(student)
        section1 = ClassSection.objects.get(id=section1.id)  ## Go get the class (and its size) again
        section2 = ClassSection.objects.get(id=section2.id)  ## Go get the class (and its size) again
        self.assertEqual(section1.num_students(), 0, "Cache error, didn't register a student being un-registered")
        self.assertEqual(section1.num_students(), section1.enrolled_students, "Triggers error, didn't update enrolled_students with the new un-enrollee")
        sm = ScheduleMap(student, program)
        self.assertTrue(len(occupied_slots(sm.map)) == 0, 'Schedule map did not clear properly.')


class BooleanLogicTest(TestCase):
    """ Verify that the Boolean logic models underlying schedule constraints are
        working correctly.
    """
    def runTest(self):
        #   Create a logic expression with default values
        exp, created = BooleanExpression.objects.get_or_create(label='bltestexp')
        a = exp.add_token('1')
        exp.add_token('not')
        b = exp.add_token('0')
        exp.add_token('not')
        exp.add_token('or')
        c = exp.add_token('0')
        exp.add_token('and')
        d = exp.add_token('1')
        e = exp.add_token('0')
        exp.add_token('and')
        exp.add_token('not')
        exp.add_token('or')

        #   Verify that it returns the right result
        self.assertTrue(exp.evaluate(), 'Incorrect Boolean logic result')

        #   Change some values and check again
        e.text = '1'
        e.save()
        self.assertFalse(exp.evaluate(), 'Incorrect Boolean logic result')

class ScheduleConstraintTest(ProgramFrameworkTest):
    """ This unit test has 2 purposes:
        1. Test the ScheduleTest* classes that act as BooleanTokens and
           compute whether certain conditions on a student's schedule are true.
        2. Test whether ScheduleConstraints can track relationships
           between the results of these tests.
    """
    def runTest(self):
        #   Initialize
        student = self.students[0]
        program = self.program
        (section_list, timeslot_list) = randomized_attrs(program)
        modules = program.getModules()
        scrmi = program.studentclassregmoduleinfo

        #   Prepare two sections
        section1 = section_list[0]
        section1.assign_start_time(timeslot_list[0])
        section1.parent_class.category = self.categories[0]
        section1.parent_class.save()
        section2 = section_list[1]
        section2.assign_start_time(timeslot_list[0])
        section2.parent_class.category = self.categories[0]
        section2.parent_class.save()

        #   Create boolean tokens
        exp1, created = BooleanExpression.objects.get_or_create(label='exp1')
        token1 = ScheduleTestOccupied(exp=exp1, timeblock=timeslot_list[0])
        token1.save()
        exp2, created = BooleanExpression.objects.get_or_create(label='exp2')
        token2 = ScheduleTestCategory(exp=exp2, timeblock=timeslot_list[0], category=self.categories[0])
        token2.save()
        exp3, created = BooleanExpression.objects.get_or_create(label='exp3')
        token3 = ScheduleTestSectionList(exp=exp3, timeblock=timeslot_list[0], section_ids='%s' % section_list[0].id)
        token3.save()

        #   Create constraints which say "if you have a class in this timeslot, it must match my {category, section list}"
        sc1 = ScheduleConstraint(program=program, condition=exp1, requirement=exp2)
        sc1.save()
        sc2 = ScheduleConstraint(program=program, condition=exp1, requirement=exp3)
        sc2.save()

        #   Test initial empty schedule
        sm = ScheduleMap(student, program)
        self.assertFalse(token1.boolean_value(map=sm.map), 'ScheduleTestOccupied broken')
        self.assertFalse(token2.boolean_value(map=sm.map), 'ScheduleTestCategory broken')
        self.assertFalse(token3.boolean_value(map=sm.map), 'ScheduleTestSectionList broken')
        self.assertTrue(sc1.evaluate(sm), 'ScheduleConstraint broken')
        self.assertTrue(sc2.evaluate(sm), 'ScheduleConstraint broken')

        #   Register for a class that meets all conditions
        section1.preregister_student(student)
        sm.populate()
        self.assertTrue(token1.boolean_value(map=sm.map), 'ScheduleTestOccupied broken')
        self.assertTrue(token2.boolean_value(map=sm.map), 'ScheduleTestCategory broken')
        self.assertTrue(token3.boolean_value(map=sm.map), 'ScheduleTestSectionList broken')
        self.assertTrue(sc1.evaluate(sm), 'ScheduleConstraint broken')
        self.assertTrue(sc2.evaluate(sm), 'ScheduleConstraint broken')

        #   Change the category and check the category constraint
        section1.parent_class.category = self.categories[1]
        section1.parent_class.save()
        sm.populate()
        self.assertTrue(token1.boolean_value(map=sm.map), 'ScheduleTestOccupied broken')
        self.assertFalse(token2.boolean_value(map=sm.map), 'ScheduleTestCategory broken')
        self.assertTrue(token3.boolean_value(map=sm.map), 'ScheduleTestSectionList broken')
        self.assertFalse(sc1.evaluate(sm), 'ScheduleConstraint broken')
        self.assertTrue(sc2.evaluate(sm), 'ScheduleConstraint broken')

        #   Change the section and check the section list constraint
        section1.unpreregister_student(student)
        section2.preregister_student(student)
        sm.populate()
        self.assertTrue(token1.boolean_value(map=sm.map), 'ScheduleTestOccupied broken')
        self.assertTrue(token2.boolean_value(map=sm.map), 'ScheduleTestCategory broken')
        self.assertFalse(token3.boolean_value(map=sm.map), 'ScheduleTestSectionList broken')
        self.assertTrue(sc1.evaluate(sm), 'ScheduleConstraint broken')
        self.assertFalse(sc2.evaluate(sm), 'ScheduleConstraint broken')

        #   Change timeslot and check that occupied is false
        section2.assign_start_time(timeslot_list[1])
        sm.populate()
        self.assertFalse(token1.boolean_value(map=sm.map), 'ScheduleTestOccupied broken')
        self.assertFalse(token2.boolean_value(map=sm.map), 'ScheduleTestCategory broken')
        self.assertFalse(token3.boolean_value(map=sm.map), 'ScheduleTestSectionList broken')
        self.assertTrue(sc1.evaluate(sm), 'ScheduleConstraint broken')
        self.assertTrue(sc2.evaluate(sm), 'ScheduleConstraint broken')

class DynamicCapacityTest(ProgramFrameworkTest):
    def runTest(self):
        #   Parameters
        initial_capacity = 37
        mult_test = decimal.Decimal('0.6')
        offset_test = 4

        #   Get class capacity
        self.program.getModules()
        sec = random.choice(list(self.program.sections()))
        # Load the SCRMI off the section, to make sure that the section doesn't
        # have a separate unupdated copy of it around when we update it.
        # (Since self.program is a different copy of the same instance from
        # sec.parent_program, if we update one SCRMI, the other won't update.)
        options = sec.parent_program.studentclassregmoduleinfo
        sec.parent_class.class_size_max = initial_capacity
        sec.parent_class.save()
        sec.max_class_capacity = initial_capacity
        sec.save()

        #   Check that initially the capacity is correct
        self.assertEqual(sec.capacity, initial_capacity)
        #   Check that multiplier works
        options.class_cap_multiplier = mult_test
        options.save()
        self.assertEqual(sec.capacity, int(initial_capacity * mult_test))
        #   Check that multiplier and offset work
        options.class_cap_offset = offset_test
        options.save()
        self.assertEqual(sec._get_capacity(), int(initial_capacity * mult_test + offset_test))
        #   Check that offset only works
        options.class_cap_multiplier = decimal.Decimal('1.0')
        options.save()
        self.assertEqual(sec.capacity, int(initial_capacity + offset_test))
        #   Check that we can go back to normal
        options.class_cap_offset = 0
        options.save()
        self.assertEqual(sec.capacity, initial_capacity)


class ModuleControlTest(ProgramFrameworkTest):
    def runTest(self):
        #   Make all default modules non-required
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        #   Pick a student and log in; fill out profile
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Check that the main student reg page displays as usual in the initial state.
        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertTrue('Steps for Registration' in six.text_type(response.content, encoding='UTF-8'))

        #   Set a student module to be required and make sure we are shown it.
        fa_module = ProgramModule.objects.filter(handler='FinancialAidAppModule')[0]
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, fa_module)
        moduleobj.__class__ = ProgramModuleObj
        moduleobj.required = True
        moduleobj.save()

        response = self.client.get(
                    '/learn/%s/studentreg' % self.program.getUrlBase(),
                    **{'wsgi.url_scheme': 'https'})
        self.assertTrue('Financial Aid' in six.text_type(response.content, encoding='UTF-8'))

        #   Remove the module and make sure we are not shown it anymore.
        self.program.program_modules.remove(fa_module)
        self.program.save()

        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertTrue('Steps for Registration' in six.text_type(response.content, encoding='UTF-8'))

class MeetingTimesTest(ProgramFrameworkTest):
    def assertSetEquals(self, a, b):
        self.assertTrue(set(a) == set(b), 'set(%s) != set(%s)' % (a, b))

    def runTest(self):
        #   Get a class section
        section = self.program.sections()[0]

        #   Make sure it is not scheduled
        section.meeting_times.clear()
        section.classroomassignments().delete()
        self.assertSetEquals(section.get_meeting_times(), [])

        #   Assign a meeting times
        ts_list = self.program.getTimeSlots()
        ts1 = ts_list[0]
        ts2 = ts_list[1]

        #   Check whether changes appear as we make them
        section.meeting_times.add(ts1)
        self.assertSetEquals(section.get_meeting_times(), [ts1])
        section.meeting_times.add(ts2)
        self.assertSetEquals(section.get_meeting_times(), [ts1, ts2])
        section.meeting_times.remove(ts1)
        self.assertSetEquals(section.get_meeting_times(), [ts2])
        section.meeting_times.remove(ts2)
        self.assertSetEquals(section.get_meeting_times(), [])

class TeacherNamesWithPronounsTest(ProgramFrameworkTest):
    def runTest(self):
        self.add_user_profiles()
        cls = self.program.classes()[0]
        teacher = cls.get_teachers()[0]
        name = teacher.name()
        info = RegistrationProfile.getLastProfile(teacher).teacher_info
        # (stored pronoun, expected display); the profile cache is keyed on
        # RegistrationProfile, so re-save it to invalidate after each change.
        cases = [(None, name), ('', name), ('   ', name),
                 ('they/them', name + ' (they/them)'),
                 (' she/her ', name + ' (she/her)')]
        for pronoun, expected in cases:
            info.pronoun = pronoun
            info.save()
            RegistrationProfile.getLastProfile(teacher).save()
            self.assertIn(expected, cls.getTeacherNamesWithPronouns())
            self.assertNotIn(name + ' ()', cls.getTeacherNamesWithPronouns())

class LSRAssignmentTest(ProgramFrameworkTest):
    def setUp(self):
        random.seed()

        # Create a program, students, classes, teachers, etc.
        super(LSRAssignmentTest, self).setUp(num_students=20, room_capacity=3)
        # Force the modules and extensions to be created
        self.program.getModules()
        # Schedule classes
        while True:
            self.schedule_randomly()
            self.timeslots = Event.objects.filter(meeting_times__parent_class__parent_program = self.program).distinct()
            # We need three timeslots with classes in them
            # for the multiple lunch constraints test
            if len(self.timeslots) >= 3:
                break

        # Create the registration types
        self.enrolled_rt, created = RegistrationType.objects.get_or_create(name='Enrolled')
        self.priority_rt, created = RegistrationType.objects.get_or_create(name='Priority/1')
        self.interested_rt, created = RegistrationType.objects.get_or_create(name='Interested')
        self.waitlist_rt, created = RegistrationType.objects.get_or_create(name='Waitlist/1')
        self.priority_rts=[self.priority_rt]
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.priority_limit = 1
        scrmi.save()

        # Add some priorities and interesteds for the lottery
        es = Event.objects.filter(program=self.program)
        for student in self.students:
            # Give the student a starting grade
            startGrade = int(random.random() * 6) + 7
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(startGrade, ESPUser.program_schoolyear(self.program)))
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()

            for e in es:
                # 0.5 prob of adding a class in the timeblock as priority
                if random.random() < 0.5:
                    sections = [s for s in self.program.sections() if e in s.meeting_times.all()]
                    if len(sections) == 0: continue
                    pri = random.choice(sections)
                    StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)
            for sec in self.program.sections():
                # 0.25 prob of adding a section as interested
                if random.random() < 0.25:
                    StudentRegistration.objects.get_or_create(user=student, section=sec, relationship=self.interested_rt)
            # Make sure the student actually entered the lottery
            if StudentRegistration.objects.filter(user=student, section__parent_class__parent_program=self.program).count() == 0:
                pri = random.choice(self.program.sections())
                StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)

    def testLottery(self):
        # Run the (legacy) lottery!
        lotteryController = LegacyLotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and check that the assignments make sense
        for student in self.students:
            # Figure out which classes they got
            interested_regs = StudentRegistration.objects.filter(user=student, relationship=self.interested_rt)
            priority_regs = StudentRegistration.objects.filter(user=student, relationship__in=self.priority_rts)
            enrolled_regs = StudentRegistration.objects.filter(user=student, relationship=self.enrolled_rt)

            interested_classes = {sr.section for sr in interested_regs}
            priority_classes = {sr.section for sr in priority_regs}
            enrolled_classes = {sr.section for sr in enrolled_regs}
            not_enrolled_classes = (priority_classes | interested_classes) - enrolled_classes
            incorrectly_enrolled_classes = enrolled_classes - (priority_classes | interested_classes)


            # Check that they can't possibly add a class they didn't get into
            for cls in not_enrolled_classes:
                self.assertTrue(cls.cannotAdd(student) or cls.isFull())

            # Check that they only got into classes that they asked for
            self.assertFalse(incorrectly_enrolled_classes)

    def testStats(self):
        """ Verify that the values returned by compute_stats() are correct
            after running the lottery.  """

        #   Run the (legacy) lottery!
        lotteryController = LegacyLotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()

        #   Get stats
        stats = lotteryController.compute_stats(display=False)

        #   Check stats for correctness
        #   - Some basic stats
        self.assertEqual(stats['num_enrolled_students'], len([x for x in self.students if len(x.getEnrolledClasses(self.program)) > 0]))
        self.assertEqual(stats['num_registrations'], len(StudentRegistration.valid_objects().filter(user__in=self.students, relationship__name='Enrolled')))
        #   - 'Screwed students' list
        for student in self.students:
            stats_entry = list([x for x in stats['students_by_screwedness'] if x[1] == student.id])
            self.assertEqual(len(stats_entry), 1)
            stats_entry = list(stats_entry)[0]

            #   Compute 'screwedness' score for this student
            sections_interested = student.getSections(self.program, verbs=['Interested'])
            sections_priority = student.getSections(self.program, verbs=['Priority/1'])
            sections_enrolled = student.getSections(self.program, verbs=['Enrolled'])

            sections_interested_and_enrolled = list((set(sections_interested) - set(sections_priority)) & set(sections_enrolled))
            sections_priority_and_enrolled = list(set(sections_priority) & set(sections_enrolled))

            hours_interested = numpy.sum([len(sec.get_meeting_times()) for sec in sections_interested_and_enrolled])
            hours_priority = numpy.sum([len(sec.get_meeting_times()) for sec in sections_priority_and_enrolled])
            student_utility = (hours_interested + 1.5 * hours_priority) ** 0.5

            student_weight = (len(sections_interested) + len(sections_priority)) ** 0.5
            student_screwed_val = (1.0 + student_utility) / (1.0 + student_weight)

            #   Compare against the value in the stats dict (allow for floating-point error)
            self.assertAlmostEqual(student_screwed_val, stats_entry[0])

    def testSingleLunchConstraint(self):
        # First generate 1 lunch timeslot
        lunch_timeslot = random.choice(self.timeslots)
        lcg = LunchConstraintGenerator(self.program, [lunch_timeslot])
        lcg.generate_all_constraints()

        lunch_sec = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
        self.assertTrue(len(lunch_sec) == 1, "Lunch constraint for one timeblock generated multiple Lunch sections")
        lunch_sec = lunch_sec[0]

        # Run the (legacy) lottery!
        lotteryController = LegacyLotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and make sure that lunch assignments make sense
        for student in self.students:
            timeslots = Event.objects.filter(meeting_times__registrations=student).exclude(meeting_times=lunch_sec)

            self.assertTrue(not lunch_sec.meeting_times.all()[0] in timeslots, "One of the student's registrations overlaps with the lunch block")

    def testMultipleLunchConstraint(self):
        # First generate 3 lunch timeslots
        lunch_timeslots = random.sample(list(self.timeslots), 3)
        lcg = LunchConstraintGenerator(self.program, lunch_timeslots)
        lcg.generate_all_constraints()

        lunch_secs = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
        self.assertTrue(len(lunch_secs) == 3, "Incorrect number of lunch sections created: %s" % (len(lunch_secs)))

        # Run the (legacy) lottery!
        lotteryController = LegacyLotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and make sure that lunch assignments make sense
        for student in self.students:
            timeslots = Event.objects.filter(meeting_times__registrations=student).exclude(meeting_times__in=lunch_secs)

            lunch_free = False
            for lunch_section in lunch_secs:
                if not lunch_section.meeting_times.all()[0] in timeslots:
                    lunch_free = True
                    break
            self.assertTrue(lunch_free, "No lunch sections free for a student!")

    def testNoLunchConstraint(self):
        # Make sure LunchConstraintGenerator won't crash with no lunch timeslots
        # (needed in case a multi-day program has lunch on some days but not others)
        lcg = LunchConstraintGenerator(self.program, [])
        lcg.generate_all_constraints()

        lunch_secs = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
        self.assertTrue(len(lunch_secs) == 0, "Lunch constraint for no timeblocks generated Lunch section")

    def testLotteryMultiplePriorities(self):
        """Creates some more priorities, then runs testLottery again."""
        self.priority_2_rt, created = RegistrationType.objects.get_or_create(name='Priority/2')
        self.priority_3_rt, created = RegistrationType.objects.get_or_create(name='Priority/3')
        self.priority_rts=[self.priority_rt, self.priority_2_rt, self.priority_3_rt]
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.priority_limit = 3
        scrmi.save()

        self.testLottery()

class SplashInfoTest(ProgramFrameworkTest):
    def test_sibling_discount_is_unique_per_student_and_program(self):
        from esp.program.models import SplashInfo

        student, other_student = self.students[:2]
        info = SplashInfo.getForUser(student, self.program)
        self.assertEqual(SplashInfo.getForUser(student, self.program).pk, info.pk)

        # The database must enforce uniqueness even on writes that bypass save().
        with self.assertRaises(IntegrityError), transaction.atomic():
            SplashInfo.objects.bulk_create([SplashInfo(student=student, program=self.program)])

        other_program = Program.objects.create(
            url='TestProgram/2223_Fall', name='Fall 2223', grade_min=7, grade_max=12)
        self.assertNotEqual(SplashInfo.getForUser(student, other_program).pk, info.pk)
        self.assertNotEqual(SplashInfo.getForUser(other_student, self.program).pk, info.pk)


class StatisticsViewTest(ProgramFrameworkTest):
    """/manage/statistics: which users a query covers, plus the None-data crashes."""

    def setUp(self):
        super(StatisticsViewTest, self).setUp(num_students=4, num_teachers=2)
        self.add_user_profiles()
        # Students 0-1 have a valid zip, student 2 a missing zip, student 3 no contact info.
        for student, zip_code in zip(self.students[:3], ['02139', '02139', None]):
            profile = RegistrationProfile.objects.get(user=student, program=self.program)
            profile.contact_user = ContactInfo.objects.create(user=student, address_zip=zip_code)
            profile.save()
        # A student who never registered for any program must not be counted.
        self.outsider = ESPUser.objects.create(username='outsider', email='outsider@learningu.org')
        self.outsider.makeRole('Student')
        RegistrationProfile.objects.create(
            user=self.outsider, most_recent_profile=True,
            student_info=StudentInfo.objects.create(user=self.outsider),
            contact_user=ContactInfo.objects.create(user=self.outsider, address_zip='90210'),
        )
        self.client.login(username=self.admins[0].username, password='password')

    def query(self, query, **extra):
        data = {
            'query': query,
            'limit': '',
            'program_type': self.program.program_type,
            'program_instance_all': 'on',
            'student_reg_type_all': 'on',
            'teacher_reg_type_all': 'on',
            'school_query_type': 'all',
            'zip_query_type': 'all',
        }
        data.update(extra)
        data = {k: v for k, v in data.items() if v is not None}
        return self.client.post('/manage/statistics/', data)

    def num_users(self, response):
        self.assertEqual(response.status_code, 200)
        match = re.search(r'(\d+) users were matched by the query', six.text_type(response.context['result']))
        self.assertIsNotNone(match, response.context['result'])
        return int(match.group(1))

    def test_all_students_means_registered_students_only(self):
        # Before the fix the reg-type filter never applied, so this counted every user on the
        # site (the outsider, teachers, admins), and the None zip crashed the sort.
        response = self.query('zipcodes')
        self.assertEqual(self.num_users(response), len(self.students))
        result = six.text_type(response.context['result'])
        self.assertIn('2 users had invalid Zip codes', result)
        self.assertIn('02139', result)
        self.assertNotIn('90210', result)

    def test_selected_student_reg_types(self):
        section = self.program.sections()[0]
        section.preregister_student(self.students[0], fast_force_create=True)
        response = self.query('zipcodes', student_reg_type_all=None, student_reg_types='classreg')
        self.assertEqual(self.num_users(response), 1)

    def test_zip_filter_uses_the_profile_for_the_selected_programs(self):
        # The filter and breakdown both use the selected program's address.
        RegistrationProfile.objects.create(
            user=self.students[0], contact_user=ContactInfo.objects.create(user=self.students[0], address_zip='94305'))
        for criteria in ({'zip_query_type': 'exact', 'zip_code': '02139'},
                         {'zip_query_type': 'partial', 'zip_code_partial': '021'}, {}):
            with self.subTest(criteria=criteria):
                _, _, result = self.run_query('zipcodes', **criteria)
                self.assertEqual(result['zip_data'], [('02139', 2)])
        self.assertEqual(self.num_users(self.query('zipcodes', zip_query_type='exact', zip_code='94305')), 0)

    def test_zip_filter_falls_back_to_the_latest_profile(self):
        # A student in a category but with no profile for the selected program: their latest profile counts.
        self.program.sections()[0].preregister_student(self.students[3], fast_force_create=True)
        RegistrationProfile.objects.filter(user=self.students[3], program=self.program).update(program=None)
        RegistrationProfile.objects.create(
            user=self.students[3], contact_user=ContactInfo.objects.create(user=self.students[3], address_zip='02139'))
        _, users, result = self.run_query('zipcodes', student_reg_type_all=None, student_reg_types='classreg',
                                          zip_query_type='exact', zip_code='02139')
        self.assertEqual(users, self.ids([self.students[3]]))
        self.assertEqual(result['zip_data'], [('02139', 1)])

    def test_zip_filter_falls_back_after_latest_profile_is_deleted(self):
        student = self.students[0]
        self.program.sections()[0].preregister_student(student, fast_force_create=True)
        RegistrationProfile.objects.filter(user=student, program=self.program).update(program=None)
        latest = RegistrationProfile.objects.create(
            user=student, contact_user=ContactInfo.objects.create(user=student, address_zip='94305'))
        latest.delete()

        _, users, result = self.run_query('zipcodes', student_reg_type_all=None, student_reg_types='classreg',
                                          zip_query_type='exact', zip_code='02139')
        self.assertEqual(users, {student.id})
        self.assertEqual(result['zip_data'], [('02139', 1)])

    def test_teacher_queries_count_teachers(self):
        response = self.query('teacher_reg')
        self.assertEqual(self.num_users(response), len(self.teachers))

    def test_demographics_with_missing_graduation_year(self):
        info = RegistrationProfile.objects.get(user=self.students[0], program=self.program).student_info
        info.graduation_year = None
        info.save()
        response = self.query('demographics')
        self.assertEqual(self.num_users(response), len(self.students))

    def test_invalid_form_over_ajax(self):
        response = self.client.post(
            '/manage/statistics/',
            {'query': 'zipcodes', 'program_type': self.program.program_type,
             'school_query_type': 'all', 'zip_query_type': 'all'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('statistics_form_contents_html', json.loads(response.content.decode('utf-8')))

    def test_heardabout_groups_punctuation_variants(self):
        from esp.program.statistics import heardabout

        class Dummy(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        form = Dummy(cleaned_data={'limit': None})
        profiles = [Dummy(student_info=Dummy(heard_about=text)) for text in ['Friend', 'friend!', 'Google']]
        result_dict = {}
        heardabout(form, [], [], profiles, result_dict)
        self.assertEqual(result_dict['heardabout_data'], [('Friend', 2), ('Google', 1)])

    def run_query(self, query, **extra):
        """Run a query through the view; return what it passed to the query function:
        (program urls, user ids, result_dict)."""
        from esp.program import statistics as statistics_functions
        seen = {}
        real = getattr(statistics_functions, query)

        def spy(form, programs, users, profiles, result_dict, **kwargs):
            seen['programs'] = sorted(p.url for p in programs)
            seen['users'] = set(users.values_list('id', flat=True))
            out = real(form, programs, users, profiles, result_dict, **kwargs)
            seen['result'] = result_dict
            return out

        with mock.patch.object(statistics_functions, query, spy):
            response = self.query(query, **extra)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', seen, 'query function not called: %r' % response.context.get('form').errors)
        self.assertEqual(self.num_users(response), len(seen['users']))
        return seen['programs'], seen['users'], seen['result']

    def ids(self, users):
        return {u.id for u in users}

    def confirm(self, student, program=None):
        Record.objects.create(user=student, event=RecordType.objects.get(name='reg_confirmed'),
                              program=program or self.program)

    def test_every_query_type_covers_the_registered_users(self):
        from esp.program.forms import StatisticsQueryForm
        for query, _ in StatisticsQueryForm.stats_questions:
            with self.subTest(query=query):
                programs, users, _ = self.run_query(query)
                self.assertEqual(programs, [self.program.url])
                expected = self.teachers if query in ('teacher_reg', 'class_reg') else self.students
                self.assertEqual(users, self.ids(expected))

    def test_overlapping_categories_count_each_user_once(self):
        section = self.program.sections()[0]
        section.preregister_student(self.students[0], fast_force_create=True)
        self.confirm(self.students[0])
        self.confirm(self.students[1])
        cases = [(['classreg'], self.students[:1]),
                 (['confirmed'], self.students[:2]),
                 (['classreg', 'confirmed'], self.students[:2])]
        for reg_types, expected in cases:
            with self.subTest(reg_types=reg_types):
                _, users, _ = self.run_query('zipcodes', student_reg_type_all=None, student_reg_types=reg_types)
                self.assertEqual(users, self.ids(expected))

    def test_no_categories_selected_counts_nobody(self):
        _, users, _ = self.run_query('zipcodes', student_reg_type_all=None)
        self.assertEqual(users, set())
        _, users, _ = self.run_query('teacher_reg', teacher_reg_type_all=None)
        self.assertEqual(users, set())

    def test_program_selection(self):
        ptype = self.program.program_type
        other_instance = Program.objects.create(url=ptype + '/2223_Fall', name=ptype + ' Fall 2223', grade_min=7, grade_max=12)
        longer_type = Program.objects.create(url=ptype + 'Extra/2223_Fall', name=ptype + 'Extra Fall 2223', grade_min=7, grade_max=12)

        programs, _, _ = self.run_query('zipcodes')
        # Every instance of the type, but not a type whose name merely starts with it.
        self.assertEqual(programs, sorted([self.program.url, other_instance.url]))
        programs, users, _ = self.run_query('zipcodes', program_instance_all=None, program_instances=[self.program.url])
        self.assertEqual(programs, [self.program.url])
        self.assertEqual(users, self.ids(self.students))
        programs, _, _ = self.run_query('zipcodes', program_instance_all=None,
                                        program_instances=[self.program.url, other_instance.url])
        self.assertEqual(programs, sorted([self.program.url, other_instance.url]))
        programs, _, _ = self.run_query('zipcodes', program_type_all='on')
        self.assertEqual(programs, sorted(Program.objects.values_list('url', flat=True)))
        self.assertIn(longer_type.url, programs)

    def test_instance_of_another_type_is_a_form_error(self):
        other = Program.objects.create(url='OtherType/2030_Fall', name='OtherType Fall 2030', grade_min=7, grade_max=12)
        response = self.query('zipcodes', program_instance_all=None, program_instances=[other.url])
        self.assertEqual(response.status_code, 200)
        self.assertIn('program_instances', response.context['form'].errors)
        self.assertNotIn('users were matched', six.text_type(response.context.get('result', '')))

    def test_school_filters(self):
        for student, school in zip(self.students, ['Alpha High', 'Alpha High', 'Beta Academy']):
            info = RegistrationProfile.objects.get(user=student, program=self.program).student_info
            info.school = school
            info.save()
        _, users, result = self.run_query('schools')
        self.assertEqual(result['school_data'], [('Alpha High', 2), ('Beta Academy', 1)])
        self.assertEqual(result['num_school'], 3)
        _, users, _ = self.run_query('schools', school_query_type='name', school_name='alpha')
        self.assertEqual(users, self.ids(self.students[:2]))
        _, users, _ = self.run_query('schools', school_query_type='list', school_multisel=['Sch:Beta Academy'])
        self.assertEqual(users, self.ids(self.students[2:3]))

    def test_zip_filters(self):
        _, users, _ = self.run_query('zipcodes', zip_query_type='exact', zip_code='02139')
        self.assertEqual(users, self.ids(self.students[:2]))
        _, users, _ = self.run_query('zipcodes', zip_query_type='partial', zip_code_partial='021')
        self.assertEqual(users, self.ids(self.students[:2]))
        # The outsider has zip 90210 but never registered, so a match on it finds nobody.
        _, users, _ = self.run_query('zipcodes', zip_query_type='partial', zip_code_partial='902')
        self.assertEqual(users, set())

    def test_teacher_categories(self):
        from esp.program.class_status import ClassStatus
        rejected_teacher, approved_teacher = self.teachers
        for cls in ClassSubject.objects.filter(parent_program=self.program, teachers=rejected_teacher):
            cls.status = ClassStatus.REJECTED
            cls.save()
        cases = [('class_approved', [approved_teacher]),
                 ('class_rejected', [rejected_teacher]),
                 ('class_proposed', [])]
        for reg_type, expected in cases:
            for query in ('teacher_reg', 'class_reg'):
                with self.subTest(reg_type=reg_type, query=query):
                    _, users, _ = self.run_query(query, teacher_reg_type_all=None, teacher_reg_types=[reg_type])
                    self.assertEqual(users, self.ids(expected))

    def test_query_results(self):
        section = self.program.sections()[0]
        section.preregister_student(self.students[0], fast_force_create=True)
        self.confirm(self.students[0])
        self.confirm(self.students[1])

        _, _, result = self.run_query('student_reg')
        (program, (student_lottery, class_lottery, enrolled, checked_in)), = result['prog_data']
        self.assertEqual(program, self.program)
        self.assertEqual((enrolled, checked_in), (1, 0))

        _, _, result = self.run_query('repeats')
        self.assertEqual(result['repeat_data'], [('1x %s' % self.program.program_type, 2)])

        _, _, result = self.run_query('startreg')
        (program, reg_dates, confirm_dates), = result['program_data']
        self.assertEqual(sum(count for _, count in reg_dates), 1)
        self.assertEqual(sum(count for _, count in confirm_dates), 2)

        _, _, result = self.run_query('teacher_reg')
        (program, (registered, approved, scheduled)), = result['prog_data']
        self.assertEqual((registered, approved), (2, 2))

        _, _, result = self.run_query('class_reg')
        (program, stats), = result['prog_data']
        self.assertEqual(stats[:2], [4, 4])  # classes registered, approved

        _, _, result = self.run_query('demographics')
        self.assertEqual(result['num_classes'], 4)
        self.assertEqual(result['gradyear_data'], [(ESPUser.program_schoolyear(self.program) + 2, 4)])

    def test_startreg_reports_undated_registrations(self):
        section, other_section = self.program.sections()[:2]
        undated, mixed = self.students[:2]
        section.preregister_student(undated, fast_force_create=True)
        section.preregister_student(mixed, fast_force_create=True)
        StudentRegistration.objects.filter(section=section, user__in=[undated, mixed]).update(start_date=None)
        other_section.preregister_student(mixed, fast_force_create=True)
        dated = StudentRegistration.objects.get(section=other_section, user=mixed)

        criteria = {'student_reg_type_all': None, 'student_reg_types': 'classreg'}
        _, _, result = self.run_query('startreg', **criteria)
        (program, first_dates, _), = result['program_data']
        self.assertEqual(program, self.program)
        self.assertEqual(first_dates, [(dated.start_date.date(), 1), (None, 1)])
        self.assertContains(self.query('startreg', **criteria), 'Unable to determine: 1 student')

    def test_demographics_vitals_and_financial_aid(self):
        from esp.program.class_status import ClassStatus
        from esp.program.models import FinancialAidRequest
        sections = list(self.program.sections().filter(status=ClassStatus.ACCEPTED))
        _, _, result = self.run_query('demographics')
        self.assertEqual(result['num_sections'], len(sections))
        self.assertEqual(result['num_class_hours'], int(sum(s.duration or 0 for s in sections)))
        self.assertEqual(result['num_student_class_hours'],
                         int(sum((s.duration or 0) * (s.parent_class.class_size_max or 0) for s in sections)))

        from decimal import Decimal
        from esp.accounting.controllers import (
            GlobalAccountingController, IndividualAccountingController, ProgramAccountingController)
        from esp.accounting.models import FinancialAidGrant, LineItemType
        FinancialAidRequest.objects.create(user=self.students[0], program=self.program, done=True, reduced_lunch=True)
        approved_request = FinancialAidRequest.objects.create(user=self.students[1], program=self.program, done=True)
        FinancialAidRequest.objects.create(user=self.students[2], program=self.program, done=False, reduced_lunch=True)
        #   Both applicants owe a fee that aid covers; only students[1] is granted aid
        GlobalAccountingController().setup_accounts()
        ProgramAccountingController(self.program).setup_accounts()
        LineItemType.objects.create(program=self.program, text='Fee', amount_dec=Decimal('10.00'),
                                    required=True, for_finaid=True)
        for student in self.students[:2]:
            IndividualAccountingController(self.program, student).ensure_required_transfers()
        FinancialAidGrant.objects.create(request=approved_request, percent=100)
        self.assertEqual([student.hasFinancialAid(self.program) for student in self.students[:2]], [False, True])
        _, _, result = self.run_query('demographics')
        self.assertEqual((result['finaid_applied'], result['finaid_lunch'], result['finaid_approved']), (2, 1, 1))

    def test_hours(self):
        section = self.program.sections()[0]
        timeslots = list(self.program.getTimeSlots()[:2])
        section.meeting_times.set(timeslots)
        section.preregister_student(self.students[0], fast_force_create=True)
        section.preregister_student(self.students[1], fast_force_create=True)
        StudentRegistration.objects.filter(user=self.students[1]).update(end_date=datetime.now() - timedelta(days=1))
        attended = RegistrationType.get_map(include=['Attended'], category='student')['Attended']
        StudentRegistration.objects.create(user=self.students[2], section=section, relationship=attended)

        _, _, result = self.run_query('hours')
        (program, enrolled, attended, _, by_slot_enrolled, by_slot_attended, num_enrolled), = result['hours_data']
        # Student 1's registration has expired, so only student 0 counts as enrolled.
        self.assertEqual((enrolled, num_enrolled), ([(2, 1)], 1))
        self.assertEqual(by_slot_enrolled, [(timeslots[0], 1), (timeslots[1], 1)])
        self.assertEqual(attended, [(2, 1)])
        self.assertEqual(by_slot_attended, [(timeslots[0], 1), (timeslots[1], 1)])

    def test_query_count_does_not_grow_with_users(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from esp.program.forms import StatisticsQueryForm

        def counts():
            result = {}
            for query, _ in StatisticsQueryForm.stats_questions:
                self.query(query)  # warm the caches
                with CaptureQueriesContext(connection) as ctx:
                    self.assertEqual(self.query(query).status_code, 200)
                result[query] = len(ctx.captured_queries)
            return result

        section = self.program.sections()[0]
        section.meeting_times.set(self.program.getTimeSlots()[:1])

        def register(student):
            section.preregister_student(student, fast_force_create=True)
            self.confirm(student)

        for student in self.students:
            register(student)
        before = counts()
        for i in range(6):
            student = ESPUser.objects.create(username='extra%d' % i, email='extra%d@learningu.org' % i)
            student.makeRole('Student')
            RegistrationProfile.objects.create(
                user=student, program=self.program, most_recent_profile=True,
                student_info=StudentInfo.objects.create(user=student, graduation_year=2030),
                contact_user=ContactInfo.objects.create(user=student, address_zip='02139'))
            register(student)
        after = counts()
        # The setup above can warm a lookup or two (after < before is fine); no query may grow.
        self.assertEqual({query: n for query, n in after.items() if n > before[query]}, {})

    def test_instance_choices_follow_selected_program_type(self):
        from esp.program.forms import StatisticsQueryForm
        other = Program.objects.create(url='OtherType/2030_Fall', name='OtherType Fall 2030', grade_min=7, grade_max=12)

        def instance_urls(form):
            return [url for url, _ in form.fields['program_instances'].choices]

        form = StatisticsQueryForm({'program_type': 'OtherType'})
        self.assertEqual(instance_urls(form), [other.url])
        form = StatisticsQueryForm({'program_type': self.program.program_type})
        self.assertIn(self.program.url, instance_urls(form))
        self.assertNotIn(other.url, instance_urls(form))
        # Unbound (first page load) or an unknown type: the first type in the list.
        first_type = StatisticsQueryForm().fields['program_type'].choices[0][0]
        for form in (StatisticsQueryForm(), StatisticsQueryForm({'program_type': 'NoSuchType'})):
            self.assertTrue(instance_urls(form))
            self.assertTrue(all(url.split('/')[0] == first_type for url in instance_urls(form)))

        # The page's re-render on a field change returns the filtered list.
        response = self.client.post('/manage/statistics/?update_form', {
            'form': 'statistics_form', 'query': 'zipcodes', 'program_type': 'OtherType',
            'program_instances': other.url, 'student_reg_type_all': 'on', 'teacher_reg_type_all': 'on',
            'school_query_type': 'all', 'zip_query_type': 'all'})
        self.assertEqual(response.status_code, 200)
        html = json.loads(response.content.decode())['statistics_form_contents_html']
        self.assertIn('value="%s"' % other.url, html)
        self.assertNotIn('value="%s"' % self.program.url, html)


class PrintableQueryTest(ProgramFrameworkTest):
    def setUp(self):
        super(PrintableQueryTest, self).setUp(num_students=4, num_teachers=4, classes_per_teacher=1)
        self.section, self.other_section = self.program.sections()[:2]
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))

    def printable(self, name, **params):
        return self.client.get('/manage/%s/%s' % (self.program.url, name), params)

    def select_users(self, users):
        user_filter = mock.Mock()
        query = Q(id__in=[user.id for user in users])
        selected = ESPUser.objects.filter(query)
        user_filter.getList.return_value = selected
        user_filter.get_Q.return_value = query
        return mock.patch('esp.users.controllers.usersearch.UserSearchController.create_filter',
                          return_value=(user_filter, True))

    def set_names(self, users):
        for user, (first, last) in zip(users, [('Zoe', 'McKay'), ('Amy', 'Baker'), ('Ada', 'McKay'), ('Ada', 'McKay')]):
            user.first_name, user.last_name = first, last
            user.save()
        # Use an explicit expected order, including the ID tie-break for the two Adas.
        return [users[index] for index in (1, 2, 3, 0)]

    def test_class_and_section_lists_render_names_with_their_phones(self):
        people = self.set_names(self.teachers)
        phones = {}
        for number, person in enumerate(self.teachers, 1):
            phones[person.id] = str(number) * 10
            RegistrationProfile.objects.create(user=person, program=self.program, contact_user=ContactInfo.objects.create(
                user=person, phone_cell=phones[person.id]))
        self.section.parent_class.teachers.set(self.teachers)
        self.section.moderators.set(self.teachers)

        names = '; '.join(person.name_last_first() for person in people)
        numbers = '; '.join(phones[person.id] for person in people)
        for route, params, prefix in (
            ('classesbyid', {'clsids': self.section.parent_class_id}, 'Section 1: '),
            ('classesbytime', {'secids': self.section.id}, ''),
        ):
            with self.subTest(route=route):
                html = self.printable(route, **params)
                cell_count = 1 if prefix else 2
                self.assertContains(html, '<td>%s</td>' % names, count=cell_count)
                self.assertContains(html, '<td>%s</td>' % numbers, count=cell_count)
                if prefix:
                    self.assertContains(html, prefix + names)
                    self.assertContains(html, prefix + numbers)

                response = self.printable(route, csv=1, **params)
                self.assertEqual(response.status_code, 200)
                _, row = list(csv.reader(response.content.decode('utf-8').splitlines()))
                self.assertEqual(row[5:9], [names, numbers, prefix + names, prefix + numbers])

    def test_roster_renders_students_in_surname_order_with_their_ids(self):
        students = self.set_names(self.students)
        self.section.moderators.add(self.teachers[0])
        for student in reversed(self.students):
            self.section.preregister_student(student, fast_force_create=True)
        with self.select_users(self.teachers[:1]):
            response = self.printable('classrostersbymoderator')
        self.assertEqual(response.status_code, 200)
        rows = re.findall(r'<td align="right">\d+</td>\s*<td>(\d+)</td>\s*<td>([^<]+)</td>',
                          response.content.decode('utf-8'))
        self.assertEqual(rows, [(str(student.id), student.name()) for student in students])

    def test_teacher_roster_handout_renders_the_roster(self):
        # The teacher-facing handout (TeacherPreviewModule.classroster) shares classroster.html
        # with the admin printables, so it must prepare the same roster fields.
        from esp.resources.models import ResourceAssignment
        teacher = self.section.parent_class.get_teachers()[0]
        event = self.timeslots[0]
        self.section.meeting_times.add(event)
        ResourceAssignment.objects.create(target=self.section, resource=Resource.objects.filter(event=event).first())
        self.section.preregister_student(self.students[0], fast_force_create=True)
        self.assertTrue(self.client.login(username=teacher.username, password='password'))
        response = self.client.get('/teach/%s/classroster' % self.program.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(six.text_type(self.section), content)
        self.assertIn('<td>%d</td>' % self.students[0].id, content)
        self.assertIn(self.students[0].name(), content)

    def test_moderator_schedule_batches_assignment_queries(self):
        from django.test.utils import CaptureQueriesContext
        from esp.resources.models import ResourceAssignment

        # Ensure the moderators selected here are not teachers of this section.
        self.section.parent_class.teachers.clear()
        self.section.moderators.set(self.teachers)
        event = self.timeslots[0]
        self.section.meeting_times.add(event)
        ResourceAssignment.objects.create(target=self.section, resource=Resource.objects.filter(event=event).first())
        table = ClassSection.moderators.through._meta.db_table
        query_counts = []
        for teachers in (self.teachers[:1], self.teachers):
            with self.select_users(teachers), CaptureQueriesContext(connection) as queries:
                response = self.printable('moderatorschedules')
            self.assertEqual(response.status_code, 200)
            self.assertEqual({item['teacher'].id for item in response.context['scheditems']},
                             {teacher.id for teacher in teachers})
            query_counts.append(sum('FROM "%s"' % table in query['sql'] for query in queries))
        self.assertGreater(query_counts[0], 0)
        self.assertLessEqual(query_counts[1], query_counts[0])

    def test_narrow_roster_does_not_fetch_unrelated_enrollments(self):
        from django.test.utils import CaptureQueriesContext
        from esp.program.modules.handlers.programprintables import ProgramPrintables

        self.section.preregister_student(self.students[0], fast_force_create=True)
        self.other_section.preregister_student(self.students[1], fast_force_create=True)
        with CaptureQueriesContext(connection) as queries:
            ProgramPrintables._prepare_rosters(self.program, [self.section])
        self.assertEqual(self.section.roster_student_ids, {self.students[0].id})
        table = StudentRegistration._meta.db_table
        enrollment_queries = [query['sql'] for query in queries if 'FROM "%s"' % table in query['sql']]
        self.assertTrue(enrollment_queries)
        with connection.cursor() as cursor:
            for sql in enrollment_queries:
                cursor.execute(sql)
                self.assertEqual(len(cursor.fetchall()), 1)

    def assign_classroom(self, section, event, name):
        from esp.resources.models import ResourceAssignment

        room = Resource.objects.create(name=name, event=event, res_type=ResourceType.get_or_create('Classroom'))
        ResourceAssignment.objects.create(target=section, resource=room)

    def test_printables_show_all_section_rooms(self):
        first, later, stale = self.timeslots
        same_start = Event.objects.create(
            program=self.program, event_type=first.event_type, start=first.start, end=first.end,
            short_description='Same start',
        )
        self.section.meeting_times.set([first, same_start, later])
        self.assign_classroom(self.section, first, 'Room Alpha')
        self.assign_classroom(self.section, first, 'Room Bravo')
        self.assign_classroom(self.section, same_start, 'Room Charlie')
        self.assign_classroom(self.section, later, 'Room Alpha')
        self.assign_classroom(self.section, later, 'Room Delta')
        self.assign_classroom(self.section, stale, 'Room Stale')
        names = ['Room Alpha', 'Room Bravo', 'Room Charlie', 'Room Delta']
        self.assertEqual(self.section.prettyrooms(), names)
        self.assertEqual([room.name for room in self.section.display_rooms()], names)

        student = self.students[0]
        self.section.preregister_student(student, fast_force_create=True)
        self.section.moderators.add(self.teachers[-1])
        for route, users, params in (
            ('classesbyid', [], {'clsids': self.section.parent_class_id}),
            ('classesbyroom', [], {'secids': self.section.id}),
            ('flatstudentschedules', [student], {}),
            ('studentschedules/tex', [student], {}),
            ('classrostersbymoderator', self.teachers[-1:], {}),
            ('moderatorschedules', self.teachers[-1:], {}),
        ):
            with self.subTest(route=route), self.select_users(users):
                response = self.printable(route, **params)
                for name in names:
                    self.assertContains(response, name, count=1)
                self.assertNotContains(response, 'Room Stale')
        for route, params in (('classesbyid', {'clsids': self.section.parent_class_id}),
                              ('classesbyroom', {'secids': self.section.id})):
            with self.subTest(route=route):
                response = self.printable(route, csv=1, **params)
                self.assertContains(response, ', '.join(names))
                self.assertNotContains(response, 'Room Stale')

    def test_classes_by_room_sorts_roomless_sections_last_then_by_time(self):
        with_z, roomless_late, with_a, roomless_early = self.program.sections()
        first, second, third = self.timeslots
        for section, event in ((with_z, first), (roomless_late, third), (with_a, third), (roomless_early, second)):
            section.meeting_times.add(event)
        self.assign_classroom(with_z, first, 'Room Z')
        self.assign_classroom(with_a, third, 'Room A')

        response = self.printable('classesbyroom')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([section.id for section in response.context['sections']],
                         [with_a.id, with_z.id, roomless_early.id, roomless_late.id])

    def test_room_timetables_use_each_assignment_in_its_own_time_slot(self):
        first, later, _ = self.timeslots
        self.section.meeting_times.set([first, later])
        self.assign_classroom(self.section, first, 'Room Alpha')
        self.assign_classroom(self.section, later, 'Room Bravo')
        moderator = self.teachers[-1]
        self.section.moderators.add(moderator)
        for route in ('roomschedules', 'roomschedules/all_blocks'):
            with self.subTest(route=route):
                response = self.printable(route)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([(item['room'], item['timeblock'].start) for item in response.context['scheditems']
                                  if item['cls'] == self.section],
                                 [('Room Alpha', first.start), ('Room Bravo', later.start)])
        response = self.printable('moderator_rooms_spr')
        self.assertEqual(response.status_code, 200)
        _, *rows = csv.reader(response.content.decode('utf-8').splitlines())
        self.assertEqual({row[0]: row[1:] for row in rows}, {
            'Room Alpha': [moderator.name(), ' ', ' '],
            'Room Bravo': [' ', moderator.name(), ' '],
        })


class UserSearchListNamesTest(ProgramFrameworkTest):
    """The user search page names its lists from the modules' description functions
    (studentDesc() etc.) instead of building the lists; both must have the same keys, in order."""

    def setUp(self):
        super(UserSearchListNamesTest, self).setUp()
        # A resource request, so the teacher lists include the dynamic per-resource ones.
        section = self.program.sections()[0]
        res_type = ResourceType.objects.create(name='Projector', description='Projector', program=self.program)
        ResourceRequest.objects.create(target=section, res_type=res_type, desired_value='Yes')

    def test_description_keys_match_list_keys(self):
        self.assertEqual(len(self.program.getModules()), ProgramModule.objects.count())
        for list_func, desc_func in zip(Program.USER_TYPE_LIST_FUNCS, Program.USER_TYPE_LIST_DESC_FUNCS):
            with self.subTest(list_func=list_func):
                list_keys = list(getattr(self.program, list_func)(QObjects=True).keys())
                self.assertTrue(list_keys)
                self.assertEqual(list(getattr(self.program, desc_func)().keys()), list_keys)
        self.assertTrue(any(key.startswith('teacher_res_') for key in self.program.teacherDesc()),
                        list(self.program.teacherDesc()))

    def test_page_lists_every_list_and_submits_one(self):
        from esp.users.controllers.usersearch import UserSearchController
        context = UserSearchController().prepare_context(self.program)
        for user_type, list_func in zip(Program.USER_TYPES_WITH_LIST_FUNCS, Program.USER_TYPE_LIST_FUNCS):
            names = [item['name'] for item in context['lists'][user_type] if not item.get('all_flag')]
            self.assertEqual(names, list(getattr(self.program, list_func)(QObjects=True).keys()))
        # Submitting a list (and a combination of two) still finds its users.
        q = UserSearchController().query_from_postdata(
            self.program, {'base_list': 'class_approved', 'recipient_type': 'Teacher'})
        self.assertEqual(set(ESPUser.objects.filter(q).distinct()), set(self.teachers))
        q = UserSearchController().query_from_postdata(
            self.program, {'combo_base_list': 'Teacher:class_submitted', 'checkbox_and_class_approved': 'on'})
        self.assertEqual(set(ESPUser.objects.filter(q).distinct()), set(self.teachers))


@unittest.skipIf(ilp_lottery.gp is None, "gurobipy is not installed")
class ILPLotteryAssignmentControllerTest(ProgramFrameworkTest):
    """Covers the parts of ILPLotteryAssignmentController that don't need
    a Gurobi license: __init__'s option validation, and _setup_pref_weight()
    (pure numpy, never touches self.model). Building/solving an actual model
    needs gurobipy installed *and* a license -- gurobipy is optional and not
    always available, so skip the whole class if it isn't importable."""

    def setUp(self):
        random.seed()

        # Create a program, students, classes, teachers, etc.
        super(ILPLotteryAssignmentControllerTest, self).setUp(num_students=20, room_capacity=3)
        self.program.getModules()
        while True:
            self.schedule_randomly()
            self.timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program).distinct()
            if len(self.timeslots) >= 3:
                break

        self.priority_rt, created = RegistrationType.objects.get_or_create(name='Priority/1')
        self.interested_rt, created = RegistrationType.objects.get_or_create(name='Interested')
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.priority_limit = 1
        scrmi.save()

        es = Event.objects.filter(program=self.program)
        for student in self.students:
            startGrade = int(random.random() * 6) + 7
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(startGrade, ESPUser.program_schoolyear(self.program)))
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()

            for e in es:
                if random.random() < 0.5:
                    sections = [s for s in self.program.sections() if e in s.meeting_times.all()]
                    if len(sections) == 0: continue
                    pri = random.choice(sections)
                    StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)
            for sec in self.program.sections():
                if random.random() < 0.25:
                    StudentRegistration.objects.get_or_create(user=student, section=sec, relationship=self.interested_rt)
            if StudentRegistration.objects.filter(user=student, section__parent_class__parent_program=self.program).count() == 0:
                pri = random.choice(self.program.sections())
                StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)

        self.program.program_size_max = 0
        self.program.save()

        # effective_priority_limit is 1 here (priority_limit=1, no grade-range
        # exceptions configured), so rank_weights needs exactly one entry.
        self.rank_weights = [3.0]

    def test_rejects_fill_low_priorities(self):
        self.assertRaises(LotteryException, ILPLotteryAssignmentController, self.program, fill_low_priorities=True)

    def test_rejects_use_student_apps(self):
        self.assertRaises(LotteryException, ILPLotteryAssignmentController, self.program, use_student_apps=True)

    def test_ignores_program_size_max(self):
        # Unlike fill_low_priorities/use_student_apps/max_sections/
        # max_timeslots, program_size_max is not rejected -- ILP silently
        # doesn't enforce it (matching the base class's existing silent
        # treatment of the program_size_by_grade Tag), and the UI carries a
        # persistent warning about that instead of blocking submission.
        self.program.program_size_max = 10
        self.program.save()
        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights, deweight_factor=0.8,
        )
        self.assertEqual(controller.program_size_max, 10)

    def test_rejects_max_sections(self):
        self.assertRaises(LotteryException, ILPLotteryAssignmentController, self.program, max_sections=2)

    def test_rejects_max_timeslots(self):
        self.assertRaises(LotteryException, ILPLotteryAssignmentController, self.program, max_timeslots=2)

    def test_rejects_use_grade_range_exceptions_flag(self):
        self.program.studentclassregmoduleinfo.use_grade_range_exceptions = True
        self.program.studentclassregmoduleinfo.save()
        self.assertRaises(
            LotteryException, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights
        )

    def test_rejects_stray_grade_range_exception_registrations(self):
        # Even with the flag off, leftover GradeRangeException rows (e.g.
        # from a program that previously had the flag on) should still block
        # ILP -- matches the DB check done during this effort, where flag
        # and rows were found out of sync on several old programs.
        self.assertFalse(self.program.useGradeRangeExceptions())
        gre_rt, _ = RegistrationType.objects.get_or_create(name='GradeRangeException')
        student = self.students[0]
        section = self.program.sections()[0]
        StudentRegistration.objects.get_or_create(user=student, section=section, relationship=gre_rt)
        self.assertRaises(
            LotteryException, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights
        )

    def test_rejects_default_rank_weights_for_non_three_level_program(self):
        # effective_priority_limit is 1 here, not 3, so there's no sane default.
        self.assertRaises(LotteryException, ILPLotteryAssignmentController, self.program)

    def test_rejects_mismatched_rank_weights_length(self):
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=[1.0, 2.0])

    def test_rejects_negative_rank_weights(self):
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=[-1.0])

    def test_rejects_negative_interest_weight(self):
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights, interest_weight=-0.5)

    def test_rejects_both_deweight_flags(self):
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights, deweight_by_section=True, deweight_by_timeslot=True)

    def test_rejects_deweight_factor_out_of_range(self):
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights, deweight_factor=1.5)
        self.assertRaises(ValueError, ILPLotteryAssignmentController, self.program, rank_weights=self.rank_weights, deweight_factor=0)

    def test_requires_deweight_factor_when_deweighting(self):
        # deweight_by_timeslot defaults True, so omitting/blanking
        # deweight_factor (as the UI does by sending null for a blank field)
        # must error rather than silently default -- no default is safe
        # since it silently changes optimization results.
        self.assertRaises(
            ValueError, ILPLotteryAssignmentController, self.program,
            rank_weights=self.rank_weights, deweight_factor=None,
        )

    def test_deweight_factor_not_required_when_deweighting_off(self):
        # With deweighting off entirely, deweight_factor is unused, so a
        # missing value must not error.
        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights,
            deweight_by_timeslot=False, deweight_by_section=False, deweight_factor=None,
        )
        self.assertIsNone(controller.deweight_factor)

    def test_pref_weight_matches_priority_and_interest(self):
        interest_weight = 0.5
        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights, interest_weight=interest_weight, check_grade=False,
            deweight_factor=0.8,
        )
        controller._setup_pref_weight()

        expected = numpy.maximum(
            controller.priority[1] * self.rank_weights[0],
            controller.interest * interest_weight,
        )
        self.assertTrue(numpy.array_equal(controller.pref_weight, expected))

        # every nonzero (student, section) pair got a variable slot, and only those
        expected_pairs = set(zip(*numpy.nonzero(expected)))
        actual_pairs = set(zip(controller.pref_student_idxs.tolist(), controller.pref_section_idxs.tolist()))
        self.assertEqual(expected_pairs, actual_pairs)

    def test_pref_weight_respects_grade_filter(self):
        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights, check_grade=True, deweight_factor=0.8,
        )
        controller._setup_pref_weight()

        grade_ok = (
            (controller.student_grades[:, None] >= controller.section_grade_min[None, :]) &
            (controller.student_grades[:, None] <= controller.section_grade_max[None, :])
        )
        expected = numpy.maximum(
            controller.priority[1] * self.rank_weights[0],
            controller.interest * 0.5,
        ) * grade_ok
        self.assertTrue(numpy.array_equal(controller.pref_weight, expected))

    def test_compute_assignments_produces_valid_schedule(self):
        # Needs an actual usable Gurobi license, not just gurobipy installed
        # (that's covered by the class-level skip) -- skip (not fail) when
        # unavailable, e.g. in CI.
        try:
            ilp_lottery.gp.Model().dispose()
        except ilp_lottery.gp.GurobiError as e:
            self.skipTest("no usable Gurobi license: %s" % e)

        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights, deweight_factor=0.8,
        )
        controller.compute_assignments()
        controller.save_assignments()

        # Every assignment corresponds to a preference the student actually expressed.
        assigned_si, assigned_sj = numpy.nonzero(controller.student_sections)
        for si, sj in zip(assigned_si, assigned_sj):
            self.assertGreater(controller.pref_weight[si, sj], 0)

        # No section is over capacity.
        self.assertTrue(numpy.all(numpy.sum(controller.student_sections, axis=0) <= controller.section_capacities))

        # Saved to the DB as real "Enrolled" StudentRegistrations.
        enrolled_count = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program, relationship__name='Enrolled',
        ).count()
        self.assertEqual(enrolled_count, int(numpy.sum(controller.student_sections)))

        # Shared stats code (inherited from Base) works unmodified on Gurobi's result.
        stats = controller.compute_stats(display=False)
        self.assertEqual(stats['num_registrations'], numpy.sum(controller.student_sections))

    def _zero_capacity_target(self):
        """A section students ranked/starred, and a ClassSection.capacity
        replacement that makes just that section's capacity 0 (as a notebook
        capacity override that disables a class does)."""
        target = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
            relationship__in=[self.priority_rt, self.interested_rt],
        ).values_list('section_id', flat=True).first()
        self.assertIsNotNone(target)
        real_capacity = ClassSection.capacity
        return target, property(lambda sec: 0 if sec.id == target else real_capacity.fget(sec))

    def test_capacity_zero_section_gets_no_empty_section_penalty(self):
        # For a capacity-0 section the default empty-section penalty collapses
        # to the single breakpoint (0, 1000), and Gurobi rejects a PWL
        # objective whose breakpoints are all at x=0 ("all x values ... differ
        # less than 1E-6"). The capacity constraint already forces enrollment
        # to 0, so the section must get no penalty variable at all. Gurobi is
        # mocked, so this runs without a license.
        target, zero_target = self._zero_capacity_target()
        with mock.patch.object(ClassSection, 'capacity', zero_target), \
                mock.patch.object(ilp_lottery, 'gp', mock.MagicMock()), \
                mock.patch.object(ilp_lottery, 'GRB', mock.MagicMock()):
            controller = ILPLotteryAssignmentController(
                self.program, rank_weights=self.rank_weights, deweight_factor=0.8,
            )
            sj = controller.section_indices[target]
            self.assertEqual(controller.section_capacities[sj], 0)
            self.assertEqual(controller._section_penalty_pwl[target][0], [0])

            controller.model = ilp_lottery.gp.Model()
            controller._setup_pref_weight()
            controller._create_vars()
            controller._setup_empty_section_penalty_pwl()

        self.assertTrue(controller.section_pref_students[sj])  # students did want it
        self.assertNotIn(sj, controller.section_enrolled_vars)
        # Other wanted sections still get one.
        self.assertTrue(controller.section_enrolled_vars)

    def test_capacity_zero_section_solves(self):
        # The same through a real solve: needs a usable Gurobi license.
        try:
            ilp_lottery.gp.Model().dispose()
        except ilp_lottery.gp.GurobiError as e:
            self.skipTest("no usable Gurobi license: %s" % e)

        target, zero_target = self._zero_capacity_target()
        with mock.patch.object(ClassSection, 'capacity', zero_target):
            controller = ILPLotteryAssignmentController(
                self.program, rank_weights=self.rank_weights, deweight_factor=0.8,
            )
            controller.compute_assignments()

        sj = controller.section_indices[target]
        self.assertEqual(int(numpy.sum(controller.student_sections[:, sj])), 0)

    def test_remote_solver_roundtrip(self):
        """build_model() -> write .mps.gz -> submit to the locally-running
        lottery-solver-service -> poll -> fetch solution ->
        apply_remote_solution() -> save_assignments(), i.e. everything
        compute_assignments() does in-process, but via the real HTTP API a
        production deployment would use. Needs both a usable Gurobi license
        (model construction happens locally either way) and
        LOTTERY_SOLVERS['local'] actually reachable -- skip rather than fail
        when either is unavailable."""

        try:
            ilp_lottery.gp.Model().dispose()
        except ilp_lottery.gp.GurobiError as e:
            self.skipTest("no usable Gurobi license: %s" % e)

        solver_config = settings.LOTTERY_SOLVERS.get('local')
        if not solver_config:
            self.skipTest("LOTTERY_SOLVERS['local'] is not configured")
        try:
            requests.get(solver_config['url'] + '/healthz', timeout=(1, 2)).raise_for_status()
        except requests.RequestException as e:
            self.skipTest("lottery-solver-service not reachable at %s: %s" % (solver_config['url'], e))

        controller = ILPLotteryAssignmentController(
            self.program, rank_weights=self.rank_weights, deweight_factor=0.8,
        )
        controller.build_model()

        # Model.write() replaces the file at this path rather than writing
        # in place (looks like write-to-temp + atomic rename internally), so
        # an already-open file object here would just keep reading the old,
        # now-unlinked empty inode -- write the path, then open it fresh.
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = "%s/model.mps.gz" % tmp_dir
            controller.model.write(tmp_path)
            with open(tmp_path, "rb") as f:
                model_bytes = f.read()
        controller.model.dispose()

        # Goes through resolve_solver_client_by_name(), not
        # RemoteSolverClient(**solver_config) directly -- the LOTTERY_SOLVERS
        # dict format (e.g. "noverify") is only meaningful once translated by
        # that function; splatting the raw config would break the moment its
        # keys stop lining up 1:1 with RemoteSolverClient's constructor.
        client = resolve_solver_client_by_name('local')
        job_id = client.submit(model_bytes, {})["job_id"]

        status = None
        deadline = time.time() + 30
        while time.time() < deadline:
            status_body = client.status(job_id)
            status = status_body["status"]
            if status in ("done", "failed", "interrupted"):
                break
            time.sleep(0.3)
        self.assertEqual(status, "done", status_body)

        solution = client.solution(job_id)
        self.assertIsNotNone(solution)
        client.delete(job_id)

        controller.apply_remote_solution(solution)
        controller.save_assignments()

        # Same checks as test_compute_assignments_produces_valid_schedule --
        # the remote round trip should produce an identical kind of result.
        assigned_si, assigned_sj = numpy.nonzero(controller.student_sections)
        for si, sj in zip(assigned_si, assigned_sj):
            self.assertGreater(controller.pref_weight[si, sj], 0)
        self.assertTrue(numpy.all(numpy.sum(controller.student_sections, axis=0) <= controller.section_capacities))
        enrolled_count = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program, relationship__name='Enrolled',
        ).count()
        self.assertEqual(enrolled_count, int(numpy.sum(controller.student_sections)))

class LotterySnapshotTest(ProgramFrameworkTest):
    """Covers BaseLotteryAssignmentController's frozen-snapshot machinery
    (snapshot_data/input_hash/encode+decode/from_snapshot/save_from_pairs)
    and the LotteryRun/LotteryInputSnapshot persistence models. None
    of this needs gurobipy or a license -- it's all Base-level and only
    reads the arrays initialize() already populates, so it uses the Legacy
    controller (any BaseLotteryAssignmentController subclass would do)."""

    def setUp(self):
        random.seed()
        super(LotterySnapshotTest, self).setUp(num_students=15, room_capacity=3)
        self.program.getModules()
        while True:
            self.schedule_randomly()
            self.timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program).distinct()
            if len(self.timeslots) >= 3:
                break

        self.priority_rt, created = RegistrationType.objects.get_or_create(name='Priority/1')
        self.interested_rt, created = RegistrationType.objects.get_or_create(name='Interested')
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.priority_limit = 1
        scrmi.save()

        es = Event.objects.filter(program=self.program)
        for student in self.students:
            # initialize() queries RegistrationProfile.graduation_year for
            # every student and indexes the (possibly empty) result as a 2D
            # array -- an empty query without any profiles at all comes back
            # 1D and blows up that indexing, so every student needs one.
            startGrade = int(random.random() * 6) + 7
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(startGrade, ESPUser.program_schoolyear(self.program)))
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()

            for e in es:
                if random.random() < 0.5:
                    sections = [s for s in self.program.sections() if e in s.meeting_times.all()]
                    if len(sections) == 0: continue
                    pri = random.choice(sections)
                    StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)
            for sec in self.program.sections():
                if random.random() < 0.25:
                    StudentRegistration.objects.get_or_create(user=student, section=sec, relationship=self.interested_rt)
            if StudentRegistration.objects.filter(user=student, section__parent_class__parent_program=self.program).count() == 0:
                pri = random.choice(self.program.sections())
                StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)

    def _enrolled_pairs(self, controller):
        return [
            (int(controller.student_ids[si]), int(controller.section_ids[sj]))
            for si, sj in zip(*numpy.nonzero(controller.student_sections))
        ]

    def test_input_hash_is_deterministic(self):
        c1 = LegacyLotteryAssignmentController(self.program)
        c2 = LegacyLotteryAssignmentController(self.program)
        self.assertEqual(c1.input_hash(), c2.input_hash())

    def test_input_hash_changes_with_data(self):
        student = self.students[0]
        section = self.program.sections()[0]
        # setUp's randomly-generated registrations can, by chance, already
        # include this exact one -- clear it first so the create() below is
        # guaranteed to actually change the input data.
        StudentRegistration.objects.filter(
            user=student, section=section, relationship=self.priority_rt,
        ).delete()

        hash_before = LegacyLotteryAssignmentController(self.program).input_hash()
        StudentRegistration.objects.create(user=student, section=section, relationship=self.priority_rt)
        hash_after = LegacyLotteryAssignmentController(self.program).input_hash()
        self.assertNotEqual(hash_before, hash_after)

    def test_snapshot_blob_round_trips(self):
        controller = LegacyLotteryAssignmentController(self.program)
        blob = controller.encode_snapshot_blob()
        decoded = BaseLotteryAssignmentController.decode_snapshot_blob(blob)
        self.assertEqual(decoded, controller.snapshot_data())

    def test_from_snapshot_matches_live_stats_with_zero_queries(self):
        live_controller = LegacyLotteryAssignmentController(self.program)
        live_controller.compute_assignments()
        live_stats = live_controller.compute_stats(display=False)

        snapshot_data = live_controller.snapshot_data()
        enrolled_pairs = self._enrolled_pairs(live_controller)

        with self.assertNumQueries(0):
            frozen_controller = BaseLotteryAssignmentController.from_snapshot(self.program, snapshot_data, enrolled_pairs)
            frozen_stats = frozen_controller.compute_stats(display=False)

        self.assertEqual(frozen_stats['num_registrations'], live_stats['num_registrations'])
        self.assertEqual(sorted(frozen_stats['section_filledness']), sorted(live_stats['section_filledness']))
        self.assertAlmostEqual(frozen_stats['overall_interest_ratio'], live_stats['overall_interest_ratio'])

    def test_from_snapshot_is_frozen_to_a_later_capacity_change(self):
        live_controller = LegacyLotteryAssignmentController(self.program)
        live_controller.compute_assignments()
        snapshot_data = live_controller.snapshot_data()
        enrolled_pairs = self._enrolled_pairs(live_controller)

        frozen_before = BaseLotteryAssignmentController.from_snapshot(self.program, snapshot_data, enrolled_pairs)
        stats_before = frozen_before.compute_stats(display=False)

        section = self.program.sections()[0]
        section.parent_class.class_size_max = (section.parent_class.class_size_max or 10) + 50
        section.parent_class.save()

        # Same snapshot_data -- re-deriving frozen stats from it must be
        # unaffected by the DB change just made.
        frozen_after = BaseLotteryAssignmentController.from_snapshot(self.program, snapshot_data, enrolled_pairs)
        stats_after = frozen_after.compute_stats(display=False)
        self.assertEqual(stats_before['total_spaces'], stats_after['total_spaces'])

    def test_save_from_pairs_creates_enrolled_registrations(self):
        sections = list(self.program.sections())[:2]
        pairs = [(self.students[0].id, sections[0].id), (self.students[1].id, sections[1].id)]

        BaseLotteryAssignmentController.save_from_pairs(self.program, pairs, try_mailman=False)

        enrolled = StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program, relationship__name='Enrolled',
        )
        self.assertEqual(enrolled.count(), 2)
        self.assertEqual({(sr.user_id, sr.section_id) for sr in enrolled}, set(pairs))

    def test_save_from_pairs_syncs_mailman_lists(self):
        """ One sync per existing list: the program list gets every lotteried
        student, a class list the students of all its sections, a section
        list its own; teachers, director and archive stay; lists that don't
        exist are skipped. """
        from esp.program.controllers.lottery import base
        cls = next(c for c in self.program.classes() if c.sections.count() >= 1)
        sections = list(cls.sections.all())
        pairs = [(self.students[0].id, sections[0].id)]
        if len(sections) > 1:
            pairs.append((self.students[1].id, sections[1].id))
        existing = {'%s-students' % cls.emailcode().lower(),
                    '%s-students' % sections[0].emailcode().lower()}
        calls = {}

        def record(name, members, keep=(), errors='raise'):
            self.assertEqual(errors, 'log')
            calls[name] = ({m.id for m in members}, set(keep))
        with override_settings(USE_MAILMAN=True, DEFAULT_EMAIL_ADDRESSES=dict(
                    settings.DEFAULT_EMAIL_ADDRESSES, archive='archive@example.com')), \
                mock.patch.object(base, 'existing_lists', return_value=existing), \
                mock.patch.object(base, 'sync_list_members', side_effect=record):
            BaseLotteryAssignmentController.save_from_pairs(
                self.program, pairs, lotteried_student_ids=[s.id for s in self.students[:3]])

        program_list = '%s_%s-students' % (self.program.program_type, self.program.program_instance)
        self.assertEqual(set(calls), {program_list} | {'%s-students' % cls.emailcode(),
                                                       '%s-students' % sections[0].emailcode()})
        self.assertEqual(calls[program_list][0], {s.id for s in self.students[:3]})
        self.assertEqual(calls['%s-students' % cls.emailcode()][0], {sid for sid, sec in pairs})
        self.assertEqual(calls['%s-students' % sections[0].emailcode()][0], {self.students[0].id})
        keep = calls['%s-students' % cls.emailcode()][1]
        self.assertTrue({'archive@example.com', self.program.director_email} <= keep)
        self.assertTrue(set(cls.get_teachers().values_list('email', flat=True)) <= keep)

    def test_save_from_pairs_expires_cached_enrollments(self):
        sections = list(self.program.sections())[:2]
        first, second = self.students[:2]

        def enrolled(student):
            return [sec.id for sec in student.getEnrolledSections(self.program)]

        BaseLotteryAssignmentController.save_from_pairs(self.program, [(first.id, sections[0].id)], try_mailman=False)
        self.assertEqual((enrolled(first), enrolled(second)), ([sections[0].id], []))  # now cached
        BaseLotteryAssignmentController.save_from_pairs(self.program, [(second.id, sections[1].id)], try_mailman=False)
        # The first student's enrollment was expired by update(), which sends no signal of its own.
        self.assertEqual((enrolled(first), enrolled(second)), ([], [sections[1].id]))

    def test_save_from_pairs_expires_every_user_and_section_cache(self):
        # invalidate_registration_caches sends one signal per distinct user and section, not
        # per registration; every user's and every section's caches must still be expired.
        sec_a, sec_b = list(self.program.sections())[:2]
        first, second = self.students[:2]

        def state():
            return ([sec.id for sec in first.getEnrolledSections(self.program)],
                    [sec.id for sec in second.getEnrolledSections(self.program)],
                    ClassSection.objects.get(id=sec_a.id).num_students(),
                    ClassSection.objects.get(id=sec_b.id).num_students())

        self.assertEqual(state(), ([], [], 0, 0))  # now cached
        BaseLotteryAssignmentController.save_from_pairs(
            self.program, [(first.id, sec_a.id), (first.id, sec_b.id), (second.id, sec_a.id)], try_mailman=False)
        self.assertEqual(state(), (sorted([sec_a.id, sec_b.id]), [sec_a.id], 2, 1))
        BaseLotteryAssignmentController.save_from_pairs(self.program, [(second.id, sec_b.id)], try_mailman=False)
        self.assertEqual(state(), ([], [sec_b.id], 0, 1))

    def test_save_assignments_expires_dropped_users_and_sections(self):
        # The legacy (dense-matrix) save path: a second save with no row for the first save's
        # student or section must still expire their caches (enrollments and section counts).
        sec_a, sec_b = list(self.program.sections())[:2]
        first, second = self.students[:2]

        def save(pairs):
            controller = BaseLotteryAssignmentController.__new__(BaseLotteryAssignmentController)
            controller.program = self.program
            controller.options = {'stats_display': False}
            controller.student_ids = numpy.array([first.id, second.id])
            controller.section_ids = numpy.array([sec_a.id, sec_b.id])
            controller.student_sections = numpy.zeros((2, 2), dtype=bool)
            for student, section in pairs:
                controller.student_sections[[first, second].index(student), [sec_a, sec_b].index(section)] = True
            controller.save_assignments(try_mailman=False)

        def state():
            return ([sec.id for sec in first.getEnrolledSections(self.program)],
                    [sec.id for sec in second.getEnrolledSections(self.program)],
                    ClassSection.objects.get(id=sec_a.id).num_students(),
                    ClassSection.objects.get(id=sec_b.id).num_students(),
                    ClassSection.objects.get(id=sec_a.id).enrolled_students)

        save([(first, sec_a)])
        self.assertEqual(state(), ([sec_a.id], [], 1, 0, 1))  # now cached
        save([(second, sec_b)])
        self.assertEqual(state(), ([], [sec_b.id], 0, 1, 0))

    def test_save_from_pairs_clears_previous_enrollments(self):
        sections = list(self.program.sections())[:2]
        BaseLotteryAssignmentController.save_from_pairs(
            self.program, [(self.students[0].id, sections[0].id)], try_mailman=False,
        )
        BaseLotteryAssignmentController.save_from_pairs(
            self.program, [(self.students[1].id, sections[1].id)], try_mailman=False,
        )

        # Last-save-wins: the first save's registration should have been
        # expired (end_date set), not left dangling as still-valid.
        valid_enrolled = StudentRegistration.objects.filter(
            StudentRegistration.is_valid_qobject(),
            section__parent_class__parent_program=self.program, relationship__name='Enrolled',
        )
        self.assertEqual(
            {(sr.user_id, sr.section_id) for sr in valid_enrolled},
            {(self.students[1].id, sections[1].id)},
        )

    def test_persistence_models_round_trip(self):
        controller = LegacyLotteryAssignmentController(self.program)
        snapshot = LotteryInputSnapshot.objects.create(
            program=self.program,
            input_hash=controller.input_hash(),
            data=controller.encode_snapshot_blob(),
        )
        run = LotteryRun.objects.create(
            program=self.program,
            snapshot=snapshot,
            solver_name='local',
            status='done',
            enrolled_pairs=[],
        )
        self.assertEqual(run.snapshot.input_hash, controller.input_hash())
        self.assertEqual(list(snapshot.runs.all()), [run])

        # Dedup is enforced at the DB level: two rows can't share input_hash.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LotteryInputSnapshot.objects.create(
                    program=self.program, input_hash=controller.input_hash(), data=b'',
                )

class LotteryRefreshTest(ProgramFrameworkTest):
    """Covers the guarded-refresh logic (esp.program.controllers.lottery.refresh)
    with a mocked RemoteSolverClient -- no gurobipy/license/solver service
    needed, since this is pure Django-DB + HTTP-client-shape logic."""

    SOLVERS = {'test': {'url': 'http://solver.invalid', 'token': 'tok'}}

    def setUp(self):
        super(LotteryRefreshTest, self).setUp()
        self.snapshot = LotteryInputSnapshot.objects.create(
            program=self.program, input_hash='0' * 64, data=b'placeholder',
        )
        self.run = LotteryRun.objects.create(
            program=self.program, snapshot=self.snapshot, solver_name='test',
            solver_job_id='job-1', status='running',
        )

    def test_terminal_run_is_noop(self):
        self.run.status = 'done'
        self.run.save()
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        MockClient.assert_not_called()

    def test_fresh_run_is_noop(self):
        self.run.last_polled_at = timezone.now()
        self.run.save()
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        MockClient.assert_not_called()

    def test_refresh_updates_status_and_progress(self):
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            instance = MockClient.return_value
            instance.status.return_value = {'status': 'running', 'progress': [{'incumbent': 1}]}
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'running')
        self.assertEqual(self.run.progress_series, [{'incumbent': 1}])
        self.assertIsNotNone(self.run.last_polled_at)
        instance.solution.assert_not_called()

    def test_refresh_captures_solution_on_terminal(self):
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            instance = MockClient.return_value
            instance.status.return_value = {'status': 'done', 'progress': []}
            instance.solution.return_value = {'stud_sec_assignment_1_2': 1.0, 'stud_sec_assignment_3_4': 0.0}
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'done')
        self.assertEqual(self.run.enrolled_pairs, [[1, 2]])
        self.assertIsNotNone(self.run.finished_at)

    def test_refresh_captures_empty_solution_on_terminal(self):
        # The solver only reports nonzero-valued variables, so a real
        # "nobody got assigned anywhere" result comes back as {} -- must
        # still be captured as enrolled_pairs=[] (a real, terminal result),
        # not left as None (which would look like "no result yet").
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            instance = MockClient.return_value
            instance.status.return_value = {'status': 'done', 'progress': []}
            instance.solution.return_value = {}
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'done')
        self.assertIsNotNone(self.run.enrolled_pairs)
        self.assertEqual(self.run.enrolled_pairs, [])

    def test_unreachable_service_sets_error_without_crashing(self):
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            instance = MockClient.return_value
            instance.status.side_effect = RemoteSolverError('boom')
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                refresh_run_from_service(self.run)
        self.run.refresh_from_db()
        self.assertIn('solver unreachable', self.run.error)
        self.assertEqual(self.run.status, 'running')

    def test_unconfigured_solver_sets_error(self):
        with override_settings(LOTTERY_SOLVERS={}):
            refresh_run_from_service(self.run)
        self.run.refresh_from_db()
        self.assertIn('not configured', self.run.error)


class LotteryGuardedRefreshConcurrencyTest(TransactionTestCase):
    """Covers the guarded-refresh advisory-lock dedup under REAL concurrent
    DB connections -- two threads, each getting its own separate Postgres
    connection (as in production: two web workers, or a poller racing a
    page load), racing to refresh the same LotteryRun. This was a known gap:
    LotteryRefreshTest (above) only proves the state-machine logic via
    mocking a single-threaded call; it never exercises whether
    pg_try_advisory_xact_lock actually serializes concurrent refreshers.

    Needs TransactionTestCase, not the usual (CacheFlushTestCase-based)
    TestCase: TestCase wraps each test in a transaction on ONE connection
    and rolls it back, so a second thread's own separate connection would
    never see setUp()'s data. TransactionTestCase actually commits (and
    truncates after the test), which real cross-connection visibility
    requires.

    Can't multiply-inherit CacheFlushTestCase(TestCase) here (conflicting
    _fixture_setup/_fixture_teardown MRO between TestCase and
    TransactionTestCase), so the cache is flushed by hand in setUp instead
    -- same reasoning as CacheFlushTestCase: argcache's memcached-backed
    @cache_function results aren't rolled back/truncated by either test
    class, and a truncate-and-recreate can reuse a Postgres id a stale
    cache entry still points at."""

    SOLVERS = {'test': {'url': 'http://solver.invalid', 'token': 'tok'}}

    def setUp(self):
        if hasattr(cache, "flush_all"):
            cache.flush_all()
        # ProgramFrameworkTest.setUp() doesn't call super().setUp() or rely
        # on any TestCase-specific machinery, so it's safe to reuse unbound
        # here even though self isn't a ProgramFrameworkTest instance --
        # avoids reimplementing its heavy Program/timeslot/section fixture.
        ProgramFrameworkTest.setUp(self)
        self.snapshot = LotteryInputSnapshot.objects.create(
            program=self.program, input_hash='1' * 64, data=b'placeholder',
        )
        self.run = LotteryRun.objects.create(
            program=self.program, snapshot=self.snapshot, solver_name='test',
            solver_job_id='job-concurrent', status='running',
        )

    def tearDown(self):
        # The worker threads below open their own raw DB connections and do
        # ORM queries outside Django's normal test-transaction wrapping,
        # which can leave Django's process-wide ContentType cache holding
        # objects whose pks get wiped by the flush() this TransactionTestCase
        # runs after every test -- causing a later test's create_permissions
        # to FK-violate against a content_type_id that no longer exists.
        ContentType.objects.clear_cache()

    def test_only_one_thread_hits_the_service(self):
        call_count = {'n': 0}
        call_count_lock = threading.Lock()
        barrier = threading.Barrier(2)
        errors = []

        class SlowClient(object):
            def status(self, job_id):
                with call_count_lock:
                    call_count['n'] += 1
                # Held while this thread's transaction (and thus its
                # advisory lock) is still open -- gives the other thread's
                # (non-blocking) lock attempt a wide window to prove it
                # backs off instead of also hitting the service.
                time.sleep(0.5)
                return {'status': 'running', 'progress': []}

        def worker():
            try:
                barrier.wait(timeout=5)
                refresh_run_from_service(LotteryRun.objects.get(pk=self.run.pk))
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        with mock.patch(
            'esp.program.controllers.lottery.refresh.resolve_solver_client',
            return_value=SlowClient(),
        ), override_settings(LOTTERY_SOLVERS=self.SOLVERS):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(
            call_count['n'], 1,
            "both threads called the solver service -- the advisory lock "
            "did not dedupe concurrent refreshers",
        )
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, 'running')
        self.assertIsNotNone(self.run.last_polled_at)


class LotterySaveConcurrencyTest(TransactionTestCase):
    """Two lottery saves for the same program, on separate connections (two web workers),
    must not interleave: the second waits for the first to commit, then expires its
    enrollments, so only the second save's remain. Without the advisory lock in
    replace_enrollments, the second save's expiry wouldn't see the first's uncommitted rows
    and both saves' enrollments would stay valid. (TransactionTestCase and the setUp/tearDown
    below for the same reasons as LotteryGuardedRefreshConcurrencyTest.)"""

    def setUp(self):
        if hasattr(cache, "flush_all"):
            cache.flush_all()
        ProgramFrameworkTest.setUp(self)

    def tearDown(self):
        ContentType.objects.clear_cache()

    def test_concurrent_saves_are_serialized(self):
        sec_a, sec_b = list(self.program.sections())[:2]
        first, second = self.students[:2]
        a_saved, release_a = threading.Event(), threading.Event()
        order, errors = [], []

        def save_a():
            try:
                with transaction.atomic():  # as a web request's transaction: the lock lasts until it ends
                    BaseLotteryAssignmentController.replace_enrollments(self.program, [(first.id, sec_a.id)])
                    a_saved.set()
                    release_a.wait(timeout=10)
                    order.append('a')
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        def save_b():
            try:
                BaseLotteryAssignmentController.replace_enrollments(self.program, [(second.id, sec_b.id)])
                order.append('b')
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        thread_a = threading.Thread(target=save_a)
        thread_a.start()
        self.assertTrue(a_saved.wait(timeout=10))
        thread_b = threading.Thread(target=save_b)
        thread_b.start()
        thread_b.join(timeout=1)
        self.assertTrue(thread_b.is_alive(), "the second save didn't wait for the first")
        release_a.set()
        thread_a.join(timeout=10)
        thread_b.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(order, ['a', 'b'])
        valid = StudentRegistration.objects.filter(
            StudentRegistration.is_valid_qobject(),
            section__parent_class__parent_program=self.program, relationship__name='Enrolled')
        self.assertEqual({(sr.user_id, sr.section_id) for sr in valid}, {(second.id, sec_b.id)})

    def test_overlapping_mailman_syncs_leave_the_latest_saved_enrollment(self):
        import lzma

        section = self.program.sections()[0]
        first, second = self.students[:2]
        snapshot = LotteryInputSnapshot.objects.create(
            program=self.program, input_hash='1' * 64,
            data=lzma.compress(json.dumps({'students': [first.id, second.id]}).encode('utf-8')),
        )
        older, newer = [
            LotteryRun.objects.create(program=self.program, snapshot=snapshot, status='done', solver_name='test',
                                      enrolled_pairs=[[student.id, section.id]])
            for student in (first, second)
        ]
        url = '/manage/%s/lottery_ilp_save' % self.program.url
        first_sync_started, release_first_sync, second_finished = (threading.Event() for _ in range(3))
        mailman_sections = {}
        responses, errors = {}, []

        def sync_mailman(program, lotteried_student_ids, students_by_section):
            if students_by_section[section.id] == [first.id]:
                first_sync_started.set()
                if not release_first_sync.wait(timeout=20):
                    raise RuntimeError('timed out waiting to finish the first Mailman sync')
            mailman_sections[section.id] = students_by_section[section.id]

        def save(run_id, client, finished=None):
            try:
                response = client.post(url, {'run_id': run_id})
                responses[run_id] = (response.status_code, json.loads(response.content)['response'][0])
            except Exception as exc:
                errors.append(exc)
            finally:
                connection.close()
                if finished is not None:
                    finished.set()

        clients = [Client(), Client()]
        for client in clients:
            self.assertTrue(client.login(username=self.admins[0].username, password='password'))
        first_thread = threading.Thread(target=save, args=(older.id, clients[0]))
        second_thread = threading.Thread(target=save, args=(newer.id, clients[1], second_finished))
        with mock.patch.object(BaseLotteryAssignmentController, 'sync_mailman_lists', side_effect=sync_mailman):
            first_thread.start()
            try:
                self.assertTrue(first_sync_started.wait(timeout=10), errors)
                self.assertFalse(connection.in_atomic_block)
                self.assertIsNotNone(LotteryRun.objects.get(pk=older.id).saved_at)
                second_thread.start()
                # A serialized implementation may block the second sync until the first finishes.
                second_finished.wait(timeout=5)
            finally:
                release_first_sync.set()
                first_thread.join(timeout=10)
                if second_thread.ident is not None:
                    second_thread.join(timeout=10)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(errors, [])
        for run in (older, newer):
            status, payload = responses[run.id]
            self.assertEqual(status, 200)
            self.assertNotIn('error_msg', payload)
        enrolled_ids = list(StudentRegistration.valid_objects().filter(
            section=section, relationship__name='Enrolled').values_list('user_id', flat=True))
        self.assertEqual(enrolled_ids, [second.id])
        self.assertEqual(mailman_sections, {section.id: enrolled_ids})


class RemoteSolverClientTimeoutTest(TestCase):
    """Covers the previously-untested gap that RemoteSolverClient's mandatory
    (connect, read) timeouts actually bound a real hang, not just that the
    timeout tuple is constructed correctly (verified by code reading only,
    per the original plan). Uses a raw TCP listener that accepts the
    connection (so connect_timeout is never in play) but never writes a
    response, exercising the read timeout specifically -- the one the
    refresh.py docstring calls out as "reintroduces hangs" if ever dropped."""

    def test_read_timeout_bounds_a_real_hang(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(('127.0.0.1', 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]
        HANG_SECONDS = 5

        def accept_and_hang():
            conn, _addr = server_sock.accept()
            try:
                conn.recv(65536)  # read (and discard) the request
                time.sleep(HANG_SECONDS)  # then just never respond
            except OSError:
                pass  # socket closed out from under us once the test finishes
            finally:
                conn.close()

        server_thread = threading.Thread(target=accept_and_hang, daemon=True)
        server_thread.start()

        client = RemoteSolverClient(
            url='http://127.0.0.1:%d' % port, token='tok',
            connect_timeout=1, read_timeout=1,
        )
        start = time.monotonic()
        with self.assertRaises(RemoteSolverError):
            client.status('job-1')
        elapsed = time.monotonic() - start

        server_sock.close()
        # Bounded by the 1s read timeout, not the server's 5s hang -- some
        # slack for scheduling jitter, but nowhere near HANG_SECONDS.
        self.assertLess(elapsed, HANG_SECONDS - 1)


class LotteryILPViewsTest(ProgramFrameworkTest):
    """Covers the lottery_ilp_* views end-to-end via the Django test
    Client. Only test_submit_creates_run_and_snapshot needs a real Gurobi
    license (build_model() actually runs) -- everything else works against
    a LotteryRun created directly, with the solver service call
    mocked, so no license/solver service is needed for those."""

    SOLVERS = {'test': {'url': 'http://solver.invalid', 'token': 'tok'}}

    def setUp(self):
        random.seed()
        super(LotteryILPViewsTest, self).setUp(num_students=15, room_capacity=3)
        self.program.getModules()
        while True:
            self.schedule_randomly()
            self.timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.program).distinct()
            if len(self.timeslots) >= 3:
                break

        self.priority_rt, created = RegistrationType.objects.get_or_create(name='Priority/1')
        self.interested_rt, created = RegistrationType.objects.get_or_create(name='Interested')
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.priority_limit = 1
        scrmi.save()
        self.program.program_size_max = 0
        self.program.save()

        es = Event.objects.filter(program=self.program)
        for student in self.students:
            startGrade = int(random.random() * 6) + 7
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(startGrade, ESPUser.program_schoolyear(self.program)))
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()
            for e in es:
                if random.random() < 0.5:
                    sections = [s for s in self.program.sections() if e in s.meeting_times.all()]
                    if len(sections) == 0: continue
                    pri = random.choice(sections)
                    StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)
            for sec in self.program.sections():
                if random.random() < 0.25:
                    StudentRegistration.objects.get_or_create(user=student, section=sec, relationship=self.interested_rt)
            if StudentRegistration.objects.filter(user=student, section__parent_class__parent_program=self.program).count() == 0:
                pri = random.choice(self.program.sections())
                StudentRegistration.objects.get_or_create(user=student, section=pri, relationship=self.priority_rt)

        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        self.url_base = self.program.getUrlBase()

    def _post(self, call_name, data=None):
        return self.client.post('/manage/%s/%s' % (self.url_base, call_name), data=data or {})

    def _response_item(self, resp):
        return json.loads(resp.content)['response'][0]

    def test_lottery_page_renders(self):
        # Only exercises page rendering, not an actual solve -- force
        # ilp_available regardless of whether gurobipy happens to be
        # installed in this environment (e.g. it isn't on CI).
        with mock.patch.object(ilp_lottery, 'gp', mock.MagicMock()), \
                override_settings(LOTTERY_SOLVERS=self.SOLVERS):
            resp = self.client.get('/manage/%s/lottery' % self.url_base)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Legacy Lottery', content)
        self.assertIn('ILP (Gurobi) Lottery', content)
        self.assertIn('lottery-mode-box active', content)
        # check_grade is a checkbox now (not a free-text True/False field),
        # and defaults to unchecked for both algorithms.
        self.assertIn('name="lottery_check_grade"', content)
        self.assertNotIn('name="lottery_check_grade" checked', content)
        self.assertIn('id="ilpCheckGrade"', content)
        self.assertNotIn('id="ilpCheckGrade" checked', content)

    def test_submit_rejects_when_no_solvers_configured(self):
        with override_settings(LOTTERY_SOLVERS={}):
            resp = self._post('lottery_ilp_submit', {'params': '{}'})
        self.assertIn('error_msg', self._response_item(resp))

    @unittest.skipIf(ilp_lottery.gp is None, "gurobipy is not installed")
    def test_submit_creates_run_and_snapshot(self):
        try:
            ilp_lottery.gp.Model().dispose()
        except ilp_lottery.gp.GurobiError as e:
            self.skipTest("no usable Gurobi license: %s" % e)

        params = json.dumps({'objective': {'rank_weights': [3.0], 'deweight_factor': 0.8}, 'label': 'test run'})
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            MockClient.return_value.submit.return_value = {'job_id': 'job-abc', 'status': 'queued'}
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                resp = self._post('lottery_ilp_submit', {'params': params})

        body = self._response_item(resp)
        self.assertNotIn('error_msg', body)
        run = LotteryRun.objects.get(id=body['run']['id'])
        self.assertEqual(run.solver_job_id, 'job-abc')
        self.assertEqual(run.status, 'queued')
        self.assertEqual(run.label, 'test run')
        self.assertEqual(run.snapshot.program, self.program)
        # random Seed was filled in even though we didn't send one
        self.assertIn('Seed', run.params['solve'])

    def test_status_view_refreshes_runs(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='1' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='running',
        )
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            MockClient.return_value.status.return_value = {'status': 'done', 'progress': []}
            MockClient.return_value.solution.return_value = {}
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                resp = self._post('lottery_ilp_status')

        runs = self._response_item(resp)['runs']
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['id'], run.id)
        self.assertEqual(runs[0]['status'], 'done')

    def test_stop_view(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='2' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='running',
        )
        with mock.patch('esp.program.controllers.lottery.refresh.RemoteSolverClient') as MockClient:
            with override_settings(LOTTERY_SOLVERS=self.SOLVERS):
                resp = self._post('lottery_ilp_stop', {'run_id': run.id})
        MockClient.return_value.stop.assert_called_once_with('job-1')
        self.assertNotIn('error_msg', self._response_item(resp))

    def _create_completed_run(self, student, section):
        legacy_controller = LegacyLotteryAssignmentController(self.program)
        snapshot = LotteryInputSnapshot.objects.create(
            program=self.program, input_hash=legacy_controller.input_hash(),
            data=legacy_controller.encode_snapshot_blob(),
        )
        return LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1',
            status='done', enrolled_pairs=[[student.id, section.id]],
        )

    def test_save_view(self):
        section = self.program.sections()[0]
        student = self.students[0]
        run = self._create_completed_run(student, section)

        with mock.patch.object(transaction, 'on_commit', wraps=transaction.on_commit) as on_commit, \
                mock.patch.object(BaseLotteryAssignmentController, 'update_mailman_lists_from_pairs') as sync_mailman:
            resp = self._post('lottery_ilp_save', {'run_id': run.id})
            self.assertNotIn('error_msg', self._response_item(resp))
            run.refresh_from_db()
            self.assertIsNotNone(run.saved_at)
            self.assertEqual(run.saved_by, self.admins[0])
            self.assertTrue(StudentRegistration.valid_objects().filter(
                user=student, section=section, relationship__name='Enrolled',
            ).exists())
            sync_mailman.assert_not_called()
            on_commit.assert_called_once()

            # TestCase rolls back its outer transaction, so run the registered callback here.
            on_commit.call_args[0][0]()
            snapshot = BaseLotteryAssignmentController.decode_snapshot_blob(bytes(run.snapshot.data))
            sync_mailman.assert_called_once_with(self.program, run.enrolled_pairs, snapshot['students'])
            section.refresh_from_db()
            self.assertEqual(section.enrolled_students, 1)

    def test_save_view_rolls_back_enrollments_if_saved_marker_fails(self):
        old_student, new_student = self.students[:2]
        section = self.program.sections()[0]
        run = self._create_completed_run(new_student, section)
        relationship = RegistrationType.objects.get(name='Enrolled')
        StudentRegistration.objects.create(user=old_student, section=section, relationship=relationship)

        with mock.patch.object(LotteryRun, 'save', side_effect=RuntimeError('marker write failed')), \
                mock.patch.object(transaction, 'on_commit', wraps=transaction.on_commit) as on_commit:
            with self.assertRaisesMessage(RuntimeError, 'marker write failed'):
                self._post('lottery_ilp_save', {'run_id': run.id})
            on_commit.assert_not_called()

        run.refresh_from_db()
        self.assertIsNone(run.saved_at)
        self.assertIsNone(run.saved_by)
        self.assertEqual(list(StudentRegistration.valid_objects().filter(
            section=section, relationship=relationship).values_list('user_id', flat=True)), [old_student.id])

    def test_save_view_mailman_retains_newer_save_when_older_callback_is_delayed(self):
        section = self.program.sections()[0]
        old_student, new_student = self.students[:2]
        older = self._create_completed_run(old_student, section)
        newer = LotteryRun.objects.create(
            program=self.program, snapshot=older.snapshot, solver_name='test', solver_job_id='job-2',
            status='done', enrolled_pairs=[[new_student.id, section.id]],
        )
        mailman_sections = {}

        def sync_mailman(program, lotteried_student_ids, students_by_section):
            mailman_sections.clear()
            mailman_sections.update(students_by_section)

        with mock.patch.object(transaction, 'on_commit', wraps=transaction.on_commit) as on_commit, \
                mock.patch.object(BaseLotteryAssignmentController, 'sync_mailman_lists', side_effect=sync_mailman):
            for run in (older, newer):
                response = self._post('lottery_ilp_save', {'run_id': run.id})
                self.assertNotIn('error_msg', self._response_item(response))
            # Simulate the older request being delayed just after committing its database changes.
            older_callback, newer_callback = [call[0][0] for call in on_commit.call_args_list]
            newer_callback()
            older_callback()

        enrolled_ids = list(StudentRegistration.valid_objects().filter(
            section=section, relationship__name='Enrolled').values_list('user_id', flat=True))
        self.assertEqual(enrolled_ids, [new_student.id])
        self.assertEqual(mailman_sections, {section.id: enrolled_ids})

    def test_save_view_syncs_mailman_when_expired_registration_section_disappears(self):
        old_section, new_section = self.program.sections()[:2]
        old_student, new_student = self.students[:2]
        run = self._create_completed_run(new_student, new_section)
        StudentRegistration.objects.create(
            user=old_student, section=old_section, relationship=RegistrationType.objects.get(name='Enrolled'))

        with mock.patch.object(transaction, 'on_commit', wraps=transaction.on_commit) as on_commit, \
                mock.patch.object(BaseLotteryAssignmentController, 'sync_mailman_lists') as sync_mailman:
            response = self._post('lottery_ilp_save', {'run_id': run.id})
            self.assertNotIn('error_msg', self._response_item(response))
            old_section.delete()
            on_commit.call_args[0][0]()

        snapshot = BaseLotteryAssignmentController.decode_snapshot_blob(bytes(run.snapshot.data))
        sync_mailman.assert_called_once_with(self.program, snapshot['students'], {new_section.id: [new_student.id]})

    def test_save_view_rejects_run_with_no_result(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='3' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='running',
        )
        resp = self._post('lottery_ilp_save', {'run_id': run.id})
        self.assertIn('error_msg', self._response_item(resp))

    def test_stats_view(self):
        legacy_controller = LegacyLotteryAssignmentController(self.program)
        snapshot = LotteryInputSnapshot.objects.create(
            program=self.program, input_hash=legacy_controller.input_hash(),
            data=legacy_controller.encode_snapshot_blob(),
        )
        section = self.program.sections()[0]
        student = self.students[0]
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1',
            status='done', enrolled_pairs=[[student.id, section.id]],
        )

        resp = self._post('lottery_ilp_stats', {'run_id': run.id})
        body = self._response_item(resp)
        self.assertNotIn('error_msg', body)
        self.assertTrue(len(body['stats']) > 0)
        self.assertTrue(len(body['charts']) > 0)

    def test_stats_view_rejects_run_with_no_result(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='5' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='running',
        )
        resp = self._post('lottery_ilp_stats', {'run_id': run.id})
        self.assertIn('error_msg', self._response_item(resp))

    def test_archive_view(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='4' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='done',
        )
        resp = self._post('lottery_ilp_archive', {'run_id': run.id})
        self.assertNotIn('error_msg', self._response_item(resp))
        run.refresh_from_db()
        self.assertTrue(run.archived)

    def test_relabel_view(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='6' * 64, data=b'x')
        run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1',
            status='running', label='original',
        )

        # Editable while still running, not just before/after -- relabeling
        # doesn't touch anything the solver cares about, just the DB row.
        resp = self._post('lottery_ilp_relabel', {'run_id': run.id, 'label': 'renamed'})
        self.assertNotIn('error_msg', self._response_item(resp))
        run.refresh_from_db()
        self.assertEqual(run.label, 'renamed')

        # Blank clears the label (stored as None, not '').
        resp = self._post('lottery_ilp_relabel', {'run_id': run.id, 'label': ''})
        self.assertNotIn('error_msg', self._response_item(resp))
        run.refresh_from_db()
        self.assertIsNone(run.label)

    def test_archived_status_and_unarchive_views(self):
        snapshot = LotteryInputSnapshot.objects.create(program=self.program, input_hash='7' * 64, data=b'x')
        active_run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-1', status='done',
        )
        archived_run = LotteryRun.objects.create(
            program=self.program, snapshot=snapshot, solver_name='test', solver_job_id='job-2',
            status='done', archived=True,
        )

        # Archived list only shows archived runs -- the mirror image of the
        # main lottery_ilp_status view, which filters archived=False.
        resp = self._post('lottery_ilp_archived_status')
        runs = self._response_item(resp)['runs']
        self.assertEqual([r['id'] for r in runs], [archived_run.id])

        resp = self._post('lottery_ilp_unarchive', {'run_id': archived_run.id})
        self.assertNotIn('error_msg', self._response_item(resp))
        archived_run.refresh_from_db()
        self.assertFalse(archived_run.archived)

        # Now shows up in the live list instead of the archived one.
        resp = self._post('lottery_ilp_status')
        self.assertEqual(
            sorted(r['id'] for r in self._response_item(resp)['runs']),
            sorted([active_run.id, archived_run.id]),
        )
        resp = self._post('lottery_ilp_archived_status')
        self.assertEqual(self._response_item(resp)['runs'], [])

class BulkCreateAccountTest(ProgramFrameworkTest):
    def setUp(self):
        super(BulkCreateAccountTest, self).setUp()
        self.client = Client()
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'),
                        'Could not login as %s' % self.admins[0].username)
        group = Group(name='BulkAccountGroup')
        group.save()

    def testHappyPath(self):
        # Make sure the bulk_create_form page works
        bulk_create_form_response = self.client.get('/manage/%s/bulk_create_form' % self.program.getUrlBase())
        self.assertEqual(bulk_create_form_response.status_code, 200)
        self.assertTrue('program/modules/bulkcreateaccountmodule/bulk_create_form.html' in
                        [x.name for x in bulk_create_form_response.templates],
                        'bulk_create_form did not render template program/modules/bulkcreateaccountmodule/bulk_create_form.html')

        # Now bulk create accounts for Student and BulkAccountGroup.
        form_data = {
            'groups': ('Student', 'BulkAccountGroup'),
            'prefix1': 'bulk1',
            'count1': '3',
            'prefix2': 'bulk2',
            'count2': '4'
        }

        bulk_account_create_response = self.client.post('/manage/%s/bulk_account_create' % self.program.getUrlBase(), data=form_data)
        self.assertEqual(bulk_account_create_response.status_code, 200)

        # make sure new accounts all exist and have the right groups
        try:
            new_accounts = []
            new_accounts.append(ESPUser.objects.get(username='bulk11'))
            new_accounts.append(ESPUser.objects.get(username='bulk12'))
            new_accounts.append(ESPUser.objects.get(username='bulk13'))
            new_accounts.append(ESPUser.objects.get(username='bulk21'))
            new_accounts.append(ESPUser.objects.get(username='bulk22'))
            new_accounts.append(ESPUser.objects.get(username='bulk23'))
            new_accounts.append(ESPUser.objects.get(username='bulk24'))

            student_group = Group.objects.get(name='Student')
            bulk_group = Group.objects.get(name='BulkAccountGroup')
            for account in new_accounts:
                self.assertTrue(student_group in account.groups.all())
                self.assertTrue(bulk_group in account.groups.all())
        except ESPUser.DoesNotExist:
            raise AssertionError('bulk_account_create did not create all accounts it was supposed to')

    def checkForBulkCreateError(self, test_case, form_data):
        bulk_account_create_response = self.client.post('/manage/%s/bulk_account_create' % self.program.getUrlBase(),
                                                        data=form_data)
        self.assertTrue('program/modules/bulkcreateaccountmodule/bulk_create_error.html' in
                        [x.name for x in bulk_account_create_response.templates],
                        'Test case "%s" did not return error page program/modules/bulkcreateaccountmodule/bulk_create_error.html' % test_case)

    def testNoPrefixes(self):
        self.checkForBulkCreateError('testNoPrefixes', {
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testTooManyAccounts(self):
        self.checkForBulkCreateError('testTooManyAccounts', {
            'prefix1': 'bulk1',
            'count1': '10000',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testMissingStudentOrTeacherGroup(self):
        self.checkForBulkCreateError('testMissingStudentOrTeacherGroup', {
            'prefix1': 'bulk1',
            'count1': '3',
            'groups': ('BulkAccountGroup')
        })

    def testBlankPrefix(self):
        self.checkForBulkCreateError('testBlankPrefix', {
            'prefix1': '    ',
            'count1': '3',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testLongPrefix(self):
        self.checkForBulkCreateError('testLongPrefix', {
            'prefix1': 'a'*100,
            'count1': '3',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testDuplicatePrefix(self):
        self.checkForBulkCreateError('testDuplicatePrefix', {
            'prefix1': 'bulk1',
            'count1': '3',
            'prefix2': 'bulk1',
            'count2': '5',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testNonNumericalCount(self):
        self.checkForBulkCreateError('testNonNumericalCount', {
            'prefix1': 'bulk1',
            'count1': 'xy',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testNegativeCount(self):
        self.checkForBulkCreateError('testNegativeCount', {
            'prefix1': 'bulk1',
            'count1': '-2',
            'groups': ('Student', 'BulkAccountGroup')
        })

    def testFractionalCount(self):
        self.checkForBulkCreateError('testFractionalCount', {
            'prefix1': 'bulk1',
            'count1': '2.6',
            'groups': ('Student', 'BulkAccountGroup')
        })


class SubmitTransactionRequiresPostTest(TestCase):
    # From LU #4855: a GET (e.g. a crawler) must not log a postback, which
    # would be listed as a failed payment and emailed to treasury
    def test_get_returns_405(self):
        from esp.accounting.models import CybersourcePostback
        response = self.client.get('/manage/submit_transaction/')
        self.assertEqual(response.status_code, 405)
        self.assertFalse(CybersourcePostback.objects.exists())
