
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
from esp.resources.models import Resource, ResourceType
from esp.users.models import ESPUser, ContactInfo, StudentInfo, TeacherInfo, Permission
from esp.web.models import NavBarCategory
from esp.tagdict.models import Tag

from django.contrib.auth.models import Group
from django.test import LiveServerTestCase
from django.test.client import Client
from django import forms

from esp.program.controllers.classreg import get_custom_fields
from esp.program.controllers.lottery import LotteryAssignmentController
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.forms import ProgramCreationForm
from esp.program.modules.base import ProgramModuleObj
from esp.program.setup import prepare_program, commit_program
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup

from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import numpy
import random
import re
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
        self.assertStringContains(response.content, 'Multiple users matched the criteria that you specified')


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
        self.assertStringContains(response.content, 'Multiple users matched the criteria that you specified')


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
        self.assertStringContains(response.content, self.admin.username)
        self.assertStringContains(response.content, self.fake_admin.username)
        self.assertStringContains(response.content, self.user.username)
        self.assertStringContains(response.content, 'href="/manage/userview?username=adminuser124353"')

        # Partial first name, not unique
        response = c.get("/manage/usersearch", { "userstr": "Adm" })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(response.content, self.admin.username)
        self.assertStringContains(response.content, self.fake_admin.username)
        self.assertNotStringContains(response.content, self.user.username)
        self.assertStringContains(response.content, 'href="/manage/userview?username=adminuser124353"')

        # Partial first name and last name, not unique
        response = c.get("/manage/usersearch", { "userstr": "Adm User" })
        self.assertEqual(response.status_code, 200)
        self.assertStringContains(response.content, self.admin.username)
        self.assertStringContains(response.content, self.fake_admin.username)
        self.assertNotStringContains(response.content, self.user.username)
        self.assertStringContains(response.content, 'href="/manage/userview?username=adminuser124353"')

        # Now, make sure we properly do nothing when there're no users to do anything to
        response = c.get("/manage/usersearch", { "userstr": "NotAUser9283490238" })
        self.assertStringContains(response.content, "No user found by that name!")
        self.assertNotStringContains(response.content, self.admin.username)
        self.assertNotStringContains(response.content, self.fake_admin.username)
        self.assertNotStringContains(response.content, self.user.username)
        self.assertNotStringContains(response.content, 'href="/manage/userview?username=adminuser124353"')


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
        self.assert_(self.user.username in response.content)
        self.assert_(self.user.first_name in response.content)
        self.assert_(self.user.last_name in response.content)
        self.assert_(str(self.user.id) in response.content)

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
        self.salt = hashlib.sha1(str(random.random())).hexdigest()[:5]

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
        self.assertEqual( self.client.login(username='ubbadmubbin', password='pubbasswubbord'), True, u'Oops, login failed!' )
    def loginTeacher(self):
        self.assertEqual( self.client.login(username='tubbeachubber', password='pubbasswubbord'), True, u'Oops, login failed!' )
    def loginStudent(self):
        self.assertEqual( self.client.login(username='stubbudubbent', password='pubbasswubbord'), True, u'Oops, login failed!' )

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
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234567@mit.edu',
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
        # TODO: Use the following line once we're officially on Django 1.1
        # self.client.post('/manage/newprogram?checked=1', {})
        self.client.get('/manage/newprogram', {'checked': '1'})

        # Now test correctness...
        self.prog = Program.by_prog_inst('Prubbogrubbam', prog_dict['term'])
        # Name
        self.assertEqual( self.prog.niceName(), u'Prubbogrubbam! Winter 3001', u'Program creation failed.' )
        # Options
        self.assertEqual(
            [unicode(x) for x in
                [self.prog.grade_min,         self.prog.grade_max,
                 self.prog.director_email,    self.prog.program_size_max] ],
            [unicode(x) for x in
                [prog_dict['grade_min'],      prog_dict['grade_max'],
                 prog_dict['director_email'], prog_dict['program_size_max']] ],
            u'Program options not properly set.' )
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
            start=now, end=now+timedelta(0,3600), event_type=timeslot_type )

        # Make some other time slots
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0,3600), end=now+timedelta(0,2*3600), event_type=timeslot_type )
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0,2*3600), end=now+timedelta(0,3*3600), event_type=timeslot_type )
        Event.objects.create(program=self.prog, description='Never', short_description='Never Ever',
            start=now+timedelta(0,3*3600), end=now+timedelta(0,4*3600), event_type=timeslot_type )

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
        self.assertEqual( unicode(self.classsubject.title), unicode(class_dict['title']), 'Failed to save title.' )

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

    def teacherreg_delete_classes(self):
        #   Check that teacher can delete the classes
        self.loginTeacher()
        user_obj = self.teacher
        target_classes = list(user_obj.getTaughtClasses())
        self.assertTrue(len(target_classes) > 0, 'Expected at least 1 class remaining to test deletion')
        while len(user_obj.getTaughtClasses()) > 0:
            class_to_delete = target_classes[0]
            del target_classes[0]

            #   Test that you can't delete a class with students in it.
            if class_to_delete.num_students() > 0:
                response = self.client.get('/teach/%s/deleteclass/%d' % (self.prog.getUrlBase(), class_to_delete.id))
                self.assertTrue('toomanystudents.html' in response.template.name)
                class_to_delete.clearStudents()

            response = self.client.get('/teach/%s/deleteclass/%d' % (self.prog.getUrlBase(), class_to_delete.id))
            self.assertTrue(set(user_obj.getTaughtClasses()) == set(target_classes), 'Could not delete class; expected to have %s, got %s' % (target_classes, user_obj.getTaughtClasses()))

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
        self.teacherreg_delete_classes()

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
            name = u'student%04d' % i
            new_student, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+u'@learningu.org')
            new_student.set_password('password')
            new_student.save()
            new_student.makeRole("Student")
            self.students.append(new_student)
        for i in range(settings['num_teachers']):
            name = u'teacher%04d' % i
            new_teacher, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+u'@learningu.org')
            new_teacher.set_password('password')
            new_teacher.save()
            new_teacher.makeRole("Teacher")
            self.teachers.append(new_teacher)
        for i in range(settings['num_admins']):
            name = u'admin%04d' % i
            new_admin, created = ESPUser.objects.get_or_create(username=name, first_name=name, last_name=name, email=name+u'@learningu.org')
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
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234567@mit.edu',
                'program_size_max': '3000',
                'program_type': settings['program_type'],
                'program_modules': settings['modules'],
                'class_categories': [x.id for x in self.categories],
                'admins': [x.id for x in self.admins],
                'teacher_reg_start': '2000-01-01 00:00:00',
                'teacher_reg_end':   '3001-01-01 00:00:00',
                'student_reg_start': '2000-01-01 00:00:00',
                'student_reg_end':   '3001-01-01 00:00:00',
                'publish_start':     '2000-01-01 00:00:00',
                'publish_end':       '3001-01-01 00:00:00',
                'base_cost':         '666',
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
        ptype_slug = re.sub('[-\s]+', '_', re.sub('[^\w\s-]', '', unicodedata.normalize('NFKD', pcf.cleaned_data['program_type']).encode('ascii', 'ignore')).strip())
        new_prog.url = ptype_slug + "/" + pcf.cleaned_data['term']
        new_prog.name = pcf.cleaned_data['program_type'] + " " + pcf.cleaned_data['term_friendly']
        new_prog.save()
        pcf.save_m2m()

        commit_program(new_prog, perms, pcf.cleaned_data['base_cost'])

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
            phone = (u'%d' % digit) * 10
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
                empty_slots = filter(lambda x: x not in ignore_ts and len(sm.map[x]) == 0, sm.map.keys())
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
                'term': '1111_Spring',
                'term_friendly': 'Spring 1111',
                'grade_min': '7',
                'grade_max': '12',
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234568@mit.edu',
                'program_size_max': '3000',
                'program_type': 'TestProgramPast',
                'program_modules': [x.id for x in ProgramModule.objects.all()],
                'class_categories': [x.id for x in self.categories],
                'admins': [x.id for x in self.admins],
                'teacher_reg_start': '1111-01-01 00:00:00',
                'teacher_reg_end':   '2000-01-01 00:00:00',
                'student_reg_start': '1111-01-01 00:00:00',
                'student_reg_end':   '2000-01-01 00:00:00',
                'publish_start':     '1111-01-01 00:00:00',
                'publish_end':       '2000-01-01 00:00:00',
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
        ptype_slug = re.sub('[-\s]+', '_', re.sub('[^\w\s-]', '', unicodedata.normalize('NFKD', pcf.cleaned_data['program_type']).encode('ascii', 'ignore')).strip())
        new_prog.url = ptype_slug + "/" + pcf.cleaned_data['term']
        new_prog.name = pcf.cleaned_data['program_type'] + " " + pcf.cleaned_data['term_friendly']
        new_prog.save()
        pcf.save_m2m()

        commit_program(new_prog, perms, pcf.cleaned_data['base_cost'])

        self.new_prog = new_prog


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
        def occupied_slots(map):
            result = []
            for key in map:
                if len(map[key]) > 0:
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
        self.assertTrue(occupied_slots(sm.map) == [ts1.id], 'Schedule map not occupied at specified timeslot.')
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
        self.assertTrue(set(sm.map[ts2.id]) == set([section1, section2]), 'Schedule map contains incorrect sections in double-booked timeslot.')

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
        self.assertTrue('Steps for Registration' in response.content)

        #   Set a student module to be required and make sure we are shown it.
        fa_module = ProgramModule.objects.filter(handler='FinancialAidAppModule')[0]
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, fa_module)
        moduleobj.__class__ = ProgramModuleObj
        moduleobj.required = True
        moduleobj.save()

        response = self.client.get(
                    '/learn/%s/studentreg' % self.program.getUrlBase(),
                    **{'wsgi.url_scheme': 'https'})
        self.assertTrue('Financial Aid' in response.content)

        #   Remove the module and make sure we are not shown it anymore.
        self.program.program_modules.remove(fa_module)
        self.program.save()

        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertTrue('Steps for Registration' in response.content)

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
        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and check that the assignments make sense
        for student in self.students:
            # Figure out which classes they got
            interested_regs = StudentRegistration.objects.filter(user=student, relationship=self.interested_rt)
            priority_regs = StudentRegistration.objects.filter(user=student, relationship__in=self.priority_rts)
            enrolled_regs = StudentRegistration.objects.filter(user=student, relationship=self.enrolled_rt)

            interested_classes = set([sr.section for sr in interested_regs])
            priority_classes = set([sr.section for sr in priority_regs])
            enrolled_classes = set([sr.section for sr in enrolled_regs])
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

        #   Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()

        #   Get stats
        stats = lotteryController.compute_stats(display=False)

        #   Check stats for correctness
        #   - Some basic stats
        self.assertEqual(stats['num_enrolled_students'], len(filter(lambda x: len(x.getEnrolledClasses(self.program)) > 0, self.students)))
        self.assertEqual(stats['num_registrations'], len(StudentRegistration.valid_objects().filter(user__in=self.students, relationship__name='Enrolled')))
        #   - 'Screwed students' list
        for student in self.students:
            stats_entry = filter(lambda x: x[1] == student.id, stats['students_by_screwedness'])[0]

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

        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and make sure that lunch assignments make sense
        for student in self.students:
            timeslots = Event.objects.filter(meeting_times__registrations=student).exclude(meeting_times=lunch_sec)

            self.assertTrue(not lunch_sec.meeting_times.all()[0] in timeslots, "One of the student's registrations overlaps with the lunch block")

    def testMultipleLunchConstraint(self):
        # First generate 3 lunch timeslots
        lunch_timeslots = random.sample(self.timeslots, 3)
        lcg = LunchConstraintGenerator(self.program, lunch_timeslots)
        lcg.generate_all_constraints()

        lunch_secs = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
        self.assertTrue(len(lunch_secs) == 3, "Incorrect number of lunch sections created: %s" % (len(lunch_secs)))

        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
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
