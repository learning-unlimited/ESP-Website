
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
  Email: web-team@lists.learningu.org
"""

from esp.datatree.models import *
from esp.users.models import UserBit, GetNode, ESPUser, StudentInfo
from esp.program.models import ClassSubject, ClassSection, RegistrationProfile, ScheduleMap, ProgramModule, StudentRegistration, RegistrationType, Event, ClassCategories
from esp.resources.models import ResourceType

from django.contrib.auth.models import User, Group
import datetime, random, hashlib

from django.test.client import Client
from esp.tests.util import CacheFlushTestCase as TestCase

from esp.program.controllers.lottery import LotteryAssignmentController
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator

import random

class ViewUserInfoTest(TestCase):
    def setUp(self):
        import random

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

        self.bit, created = UserBit.objects.get_or_create(user=self.admin, verb=GetNode("V/Administer"), qsc=GetNode("Q"))

    def assertStringContains(self, string, contents):
        if not (contents in string):
            self.assert_(False, "'%s' not in '%s'" % (contents, string))

    def assertNotStringContains(self, string, contents):
        if contents in string:
            self.assert_(False, "'%s' are in '%s' and shouldn't be" % (contents, string))
            
    def testUserSearchFn(self):
        """
        Tests whether the user-search page works properly.
        Note that this doubles as a test of the find_user function,
        because this page is a very lightweight wrapper around that function.
        """
        c = Client()
        c.login(username=self.admin.username, password=self.password)

        # Try searching by ID
        response = c.get("/manage/usersearch", { "userstr": str(self.admin.id) })
        self.assertEqual(response.status_code, 302)
        self.assertStringContains(response['location'], "/manage/userview?username=adminuser124353")

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
        response = c.get("/manage/usersearch", { "userstr": "Admin User" })
        self.assertEqual(response.status_code, 302)
        self.assertStringContains(response['location'], "/manage/userview?username=adminuser124353")

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
        self.failUnless( c.login(username=self.admin.username, password=self.password), "Couldn't log in as admin" )

        # Test to make sure we can get a user's page
        # (I'm just going to assume that the template renders properly;
        # too lame to do a real thorough test of it...)
        response = c.get("/manage/userview", { 'username': self.user.username })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].id, self.user.id)
        self.assert_(self.admin.first_name in response.content)

        # Test to make sure we get an error on an unknown user
        response = c.get("/manage/userview", { 'username': "NotARealUser" })
        self.assertEqual(response.status_code, 500)

        # Now, make sure that only admins can view this page
        self.failUnless( c.login(username=self.fake_admin.username, password=self.password), "Couldn't log in as fake admin" )
        response = c.get("/manage/userview", { 'username': self.user.username })
        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        self.bit.delete()
        self.user.delete()
        self.admin.delete()
        self.fake_admin.delete()
        
        
        
class ProfileTest(TestCase):

    def setUp(self):
        self.salt = hashlib.sha1(str(random.random())).hexdigest()[:5]

    def testAcctCreate(self):
        self.u=ESPUser(
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
        #print self.u.__dict__
        #print self.u.groups.all()


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
        from esp.datatree.models import DataTree, GetNode
        from esp.datatree.models import install as datatree_install
        from esp.users.models import ESPUser, UserBit
        
        # make program type, since we can't do that yet
        self.program_type_anchor = GetNode('Q/Programs/Prubbogrubbam')
        self.program_type_anchor.friendly_name = u'Prubbogrubbam!'
        self.program_type_anchor.save()
        
        def makeuser(f, l, un, email, p):
            u = ESPUser(first_name=f, last_name=l, username=un, email=email)
            u.set_password(p)
            u.save()
            return ESPUser(u)
        
        # make people -- presumably we're testing actual account creation elsewhere
        self.admin = makeuser('Ubbad', 'Mubbin', 'ubbadmubbin', 'ubbadmubbin@esp.mit.edu', 'pubbasswubbord')
        self.student = makeuser('Stubbu', 'Dubbent', 'stubbudubbent', 'stubbudubbent@esp.mit.edu', 'pubbasswubbord')
        self.teacher = makeuser('Tubbea', 'Chubber', 'tubbeachubber', 'tubbeachubber@esp.mit.edu', 'pubbasswubbord')
        
        UserBit.objects.create(user=self.admin, verb=GetNode('V/Flags/UserRole/Administrator'), qsc=GetNode('Q'), recursive=False)
        UserBit.objects.create(user=self.admin, verb=GetNode('V/Administer'), qsc=GetNode('Q/Programs/Prubbogrubbam'))
        UserBit.objects.create(user=self.student, verb=GetNode('V/Flags/UserRole/Student'), qsc=GetNode('Q'), recursive=False)
        UserBit.objects.create(user=self.teacher, verb=GetNode('V/Flags/UserRole/Teacher'), qsc=GetNode('Q'), recursive=False)
    
    def makeprogram(self):
        """ Test program creation through the web form. """
        from esp.users.models import ESPUser
        from esp.program.models import Program, ProgramModule, ClassCategories
        from esp.program.modules.base import ProgramModuleObj
        from esp.accounting_core.models import LineItemType
        from decimal import Decimal
        # Imports for the HttpRequest hack
        from esp.program.views import newprogram
        from django.http import HttpRequest
        
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
                'class_size_min': '0',
                'class_size_max': '500',
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234567@mit.edu',
                'program_size_max': '3000',
                'anchor': self.program_type_anchor.id,
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
                'finaid_cost':       '37',
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
                 self.prog.class_size_min,    self.prog.class_size_max,
                 self.prog.director_email,    self.prog.program_size_max] ],
            [unicode(x) for x in
                [prog_dict['grade_min'],      prog_dict['grade_max'],
                 prog_dict['class_size_min'], prog_dict['class_size_max'],
                 prog_dict['director_email'], prog_dict['program_size_max']] ],
            u'Program options not properly set.' )
        # Anchor
        self.assertEqual( self.prog.anchor, self.program_type_anchor[prog_dict['term']], u'Anchor not properly set.' )
        # Program Cost
        self.assertEqual(
            Decimal(-LineItemType.objects.get(anchor__name="Required", anchor__parent__parent=self.prog.anchor).amount),
            Decimal(prog_dict['base_cost']),
            'Program admission cost not set properly.' )
    
    def teacherreg(self):
        """ Test teacher registration (currently just class reg) through the web form. """

        # Just register a class for now.
        # Make rooms & times, since I'm too lazy to do that as a test just yet.
        from esp.cal.models import EventType, Event
        from esp.resources.models import Resource, ResourceType, ResourceAssignment
        from esp.program.controllers.classreg import get_custom_fields
        from django import forms
        from datetime import datetime

        self.failUnless( self.prog.classes().count() == 0, 'Website thinks empty program has classes')
        user_obj = ESPUser.objects.get(username='tubbeachubber')
        self.failUnless( user_obj.getTaughtClasses().count() == 0, "User tubbeachubber is teaching classes that don't exist")
        self.failUnless( user_obj.getTaughtSections().count() == 0, "User tubbeachubber is teaching sections that don't exist")
        
        timeslot_type = EventType.objects.create(description='Class Time Block')
        self.timeslot = Event.objects.create(anchor=self.prog.anchor, description='Never', short_description='Never Ever',
            start=datetime(3001,1,1,12,0), end=datetime(3001,1,1,13,0), event_type=timeslot_type )

        # Make some other time slots
        Event.objects.create(anchor=self.prog.anchor, description='Never', short_description='Never Ever',
            start=datetime(3001,1,1,13,0), end=datetime(3001,1,1,14,0), event_type=timeslot_type )
        Event.objects.create(anchor=self.prog.anchor, description='Never', short_description='Never Ever',
            start=datetime(3001,1,1,14,0), end=datetime(3001,1,1,15,0), event_type=timeslot_type )
        Event.objects.create(anchor=self.prog.anchor, description='Never', short_description='Never Ever',
            start=datetime(3001,1,1,15,0), end=datetime(3001,1,1,16,0), event_type=timeslot_type )

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
        }
        """
            #   Additional keys to test resource forms:
            'request-TOTAL_FORMS': '2',
            'request-INITIAL_FORMS': '2',
            'request-0-resource_type': str(ResourceType.get_or_create('Classroom').id),
            'request-0-desired_value': 'Lecture',
            'request-1-resource_type': str(ResourceType.get_or_create('A/V').id),
            'request-1-desired_value': 'LCD projector',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
        """
        
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

        # check the title and anchor are good
        self.assertEqual( unicode(self.classsubject.anchor.name), unicode(self.classsubject.emailcode()), 'Anchor saved incorrectly as "%s".' % self.classsubject.anchor.uri )
        self.assertEqual( unicode(self.classsubject.title()), unicode(class_dict['title']), 'Failed to save title.' )

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
        from esp.users.models import ContactInfo, StudentInfo, UserBit
        from esp.program.models import RegistrationProfile, StudentRegistration
        from datetime import datetime, timedelta

        # Check that you're in no classes
        self.assertEqual( self.student.getEnrolledClasses().count(), 0, "Student incorrectly enrolled in a class" )
        self.assertEqual( self.student.getEnrolledSections().count(), 0, "Student incorrectly enrolled in a section")
        
        # Approve and schedule a class, because I'm too lazy to have this run as a test just yet.
        self.classsubject.accept()
        sec = self.classsubject.sections.all()[0]
        sec.meeting_times.add(self.timeslot)
        sec.assignClassRoom(self.classroom)
        
        # shortcut student profile creation -- presumably we're also testing this elsewhere
        thisyear = datetime.now().year
        prof = RegistrationProfile.getLastForProgram(self.student, self.prog)
        prof.contact_user = ContactInfo.objects.create( user=self.student, first_name=self.student.first_name, last_name=self.student.last_name, e_mail=self.student.email )
        prof.student_info = StudentInfo.objects.create( user=self.student, graduation_year=thisyear+2, dob=datetime(thisyear-15, 1, 1) )
        prof.save()
        
        # Student logs in and signs up for classes
        self.loginStudent()
        self.client.get('%sstudentreg' % self.prog.get_learn_url())
        reg_dict = {
            'class_id': self.classsubject.id,
            'section_id': sec.id,
        }
        
        # Try signing up for a class.
        self.client.post('%saddclass' % self.prog.get_learn_url(), reg_dict)

        sr = StudentRegistration.objects.all()[0]
        #print "StudentRegTest", StudentRegistration.valid_objects().all(), self.student.id, sec.id, self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb.id, sr.user.id, sr.section.id, sr.relationship.id, StudentRegistration.valid_objects().filter(user=self.student, section=sec, relationship=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb), StudentRegistration.valid_objects().filter(user=self.student, section=sec, relationship=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb).count(), StudentRegistration.valid_objects().filter(user=self.student, section=sec, relationship=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb).count() > 0

        self.assertTrue( StudentRegistration.valid_objects().filter(user=self.student, section=sec,
            relationship=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb).count() > 0, 'Registration failed.')

        # Check that you're in it now
        self.assertEqual( self.student.getEnrolledClasses().count(), 1, "Student not enrolled in exactly one class" )
        self.assertEqual( self.student.getEnrolledSections().count(), 1, "Student not enrolled in exactly one section" )
        
        # Try dropping a class.
        self.client.get('%sclearslot/%s' % (self.prog.get_learn_url(), self.timeslot.id))
        self.assertFalse( StudentRegistration.valid_objects().filter(user=self.student, section=sec,
            relationship=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb).count() > 0, 'Registration failed.')

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
        from esp.users.models import ESPUser
        from esp.cal.models import Event, EventType
        from esp.resources.models import Resource, ResourceType
        from esp.program.models import ProgramModule, Program, ClassCategories, ClassSubject
        from esp.program.setup import prepare_program, commit_program
        from esp.program.forms import ProgramCreationForm
        from esp.qsd.models import QuasiStaticData
        from esp.web.models import NavBarCategory
        from datetime import datetime, timedelta
        
        #   Force Datatree to not use transactions
        import esp.datatree.sql.set_isolation_level
        esp.datatree.sql.set_isolation_level.DISABLE_TRANSACTIONS = True
        
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
                    'modules': [x.id for x in ProgramModule.objects.all()],
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

        #   Make an anchor for the program type
        self.program_type_anchor = GetNode('Q/Programs/%s' % settings['program_type'])

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
            new_student, created = ESPUser.objects.get_or_create(username='student%04d' % i)
            new_student.set_password('password')
            new_student.save()
            role_bit, created = UserBit.objects.get_or_create(user=new_student, verb=GetNode('V/Flags/UserRole/Student'), qsc=GetNode('Q'), recursive=False)
            self.students.append(ESPUser(new_student)) 
        for i in range(settings['num_teachers']):
            new_teacher, created = ESPUser.objects.get_or_create(username='teacher%04d' % i)
            new_teacher.set_password('password')
            new_teacher.save()
            role_bit, created = UserBit.objects.get_or_create(user=new_teacher, verb=GetNode('V/Flags/UserRole/Teacher'), qsc=GetNode('Q'), recursive=False)
            self.teachers.append(ESPUser(new_teacher))
        for i in range(settings['num_admins']):
            new_admin, created = ESPUser.objects.get_or_create(username='admin%04d' % i)
            new_admin.set_password('password')
            new_admin.save()
            role_bit, created = UserBit.objects.get_or_create(user=new_admin, verb=GetNode('V/Flags/UserRole/Administrator'), qsc=GetNode('Q'), recursive=False)
            self.admins.append(ESPUser(new_admin))
            
        #   Establish attributes for program
        prog_form_values = {
                'term': settings['program_instance_name'],
                'term_friendly': settings['program_instance_label'],
                'grade_min': '7',
                'grade_max': '12',
                'class_size_min': '0',
                'class_size_max': '500',
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234567@mit.edu',
                'program_size_max': '3000',
                'anchor': self.program_type_anchor.id,
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
                'finaid_cost':       '37',
            }        

        #   Create the program much like the /manage/newprogram view does
        pcf = ProgramCreationForm(prog_form_values)
        if not pcf.is_valid():
            print "ProgramCreationForm errors"
            print pcf.data
            print pcf.errors
            print prog_form_values
            raise Exception()
        
        temp_prog = pcf.save(commit=False)
        datatrees, userbits, modules = prepare_program(temp_prog, pcf.cleaned_data)
        costs = (pcf.cleaned_data['base_cost'], pcf.cleaned_data['finaid_cost'])
        anchor = GetNode(pcf.cleaned_data['anchor'].get_uri() + "/" + pcf.cleaned_data["term"])
        anchor.friendly_name = pcf.cleaned_data['term_friendly']
        anchor.save()
        new_prog = pcf.save(commit=False)
        new_prog.anchor = anchor
        new_prog.save()
        pcf.save_m2m()
        commit_program(new_prog, datatrees, userbits, modules, costs)
        self.program = new_prog
            
        #   Create timeblocks and resources
        self.event_type, created = EventType.objects.get_or_create(description='Default Event Type')
        for i in range(settings['num_timeslots']):
            start_time = settings['start_time'] + timedelta(minutes=i * (settings['timeslot_length'] + settings['timeslot_gap']))
            end_time = start_time + timedelta(minutes=settings['timeslot_length'])
            event, created = Event.objects.get_or_create(anchor=self.program.anchor, event_type=self.event_type, start=start_time, end=end_time, short_description='Slot %i' % i, description=start_time.strftime("%H:%M %m/%d/%Y"))
        self.timeslots = self.program.getTimeSlots()
        for i in range(settings['num_rooms']):
            for ts in self.timeslots:
                res, created = Resource.objects.get_or_create(name='Room %d' % i, num_students=settings['room_capacity'], event=ts, res_type=ResourceType.get_or_create('Classroom'))
        self.rooms = self.program.getClassrooms()
                   
        #   Create classes and sections
        subject_count = 0
        class_dummy_anchor = GetNode('Q/DummyClass')
        for t in self.teachers:
            for i in range(settings['classes_per_teacher']):
                current_category = self.categories[subject_count % settings['num_categories']]
                class_anchor = GetNode('%s/Classes/%s%d' % (self.program.anchor.get_uri(), current_category.symbol, subject_count + 1))
                new_class, created = ClassSubject.objects.get_or_create(anchor=class_anchor, category=current_category, grade_min=7, grade_max=12, parent_program=self.program, class_size_max=settings['room_capacity'], class_info='Description %d!' % subject_count)
                new_class.makeTeacher(t)
                subject_count += 1
                for j in range(settings['sections_per_class']):
                    if new_class.get_sections().count() <= j:
                        new_class.add_section(duration=settings['timeslot_length']/60.0)
                new_class.accept() 

        #   Give the program its own QSD main-page
        QuasiStaticData.objects.get_or_create(path=new_prog.anchor,
                                              name="learn:index",
                                              title=new_prog.niceName(),
                                              content="Welcome to %s!  Click <a href='studentreg'>here</a> to go to Student Registration.  Click <a href='catalog'>here</a> to view the course catalog.",
                                              author=self.admins[0],
                                              nav_category=NavBarCategory.objects.get_or_create(name="learn", long_explanation="")[0])


    #   Helper function to give the program a schedule.
    #   Does not get called by default, but subclasses can call it.
    def schedule_randomly(self):
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
                        #   print '%s -> %s at %s' % (sec, sec.start_time().short_time(), sec.initial_rooms()[0].name)

    #   Helper function to give each student a profile so they can sign up for classes.
    #   Does not get called by default, but subclasses can call it.
    def add_student_profiles(self):
        for student in self.students:
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(10))
            student_studentinfo.save()
            student_regprofile = RegistrationProfile(user=student, program=self.program, student_info=student_studentinfo, most_recent_profile=True)
            student_regprofile.save()
            
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
        from esp.program.models import ProgramModule
        from esp.program.forms import ProgramCreationForm
        from esp.program.setup import prepare_program, commit_program
        # Make a program
        prog_form_values = {
                'term': '1111_Spring',
                'term_friendly': 'Spring 1111',
                'grade_min': '7',
                'grade_max': '12',
                'class_size_min': '0',
                'class_size_max': '500',
                'director_email': '123456789-223456789-323456789-423456789-523456789-623456789-7234568@mit.edu',
                'program_size_max': '3000',
                'anchor': self.program_type_anchor.id,
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
            print "ProgramCreationForm errors"
            print pcf.data
            print pcf.errors
            print prog_form_values
            raise Exception()
        temp_prog = pcf.save(commit=False)
        datatrees, userbits, modules = prepare_program(temp_prog, pcf.cleaned_data)
        costs = (pcf.cleaned_data['base_cost'], pcf.cleaned_data['finaid_cost'])
        anchor = GetNode(pcf.cleaned_data['anchor'].get_uri() + "/" + pcf.cleaned_data["term"])
        anchor.friendly_name = pcf.cleaned_data['term_friendly']
        anchor.save()
        new_prog = pcf.save(commit=False)
        new_prog.anchor = anchor
        new_prog.save()
        pcf.save_m2m()
        commit_program(new_prog, datatrees, userbits, modules, costs)
        self.new_prog = new_prog

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
        from esp.program.models import ScheduleMap, ProgramModule
        from esp.program.modules.base import ProgramModuleObj
        
        import random
        
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
        scrmi = program.getModuleExtension('StudentClassRegModuleInfo', ProgramModuleObj.objects.filter(program=program, module__handler='StudentClassRegModule')[0].id)
        
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
        from esp.program.models import BooleanExpression
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
        from esp.program.models import BooleanExpression, ScheduleMap, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ScheduleTestSectionList
        from esp.program.modules.base import ProgramModuleObj
        
        #   Initialize
        student = self.students[0]
        program = self.program
        (section_list, timeslot_list) = randomized_attrs(program)
        modules = program.getModules()
        scrmi = program.getModuleExtension('StudentClassRegModuleInfo', ProgramModuleObj.objects.filter(program=program, module__handler='StudentClassRegModule')[0].id)
 
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
        mult_test = 0.6
        offset_test = 4
    
        #   Get class capacity
        self.program.getModules()
        options = self.program.getModuleExtension('StudentClassRegModuleInfo')
        sec = random.choice(list(self.program.sections()))
        sec.parent_class.class_size_max = initial_capacity
        sec.parent_class.save()
        sec.max_class_capacity = initial_capacity
        sec.save()
        
        #   Check that initially the capacity is correct
        sec.parent_class._moduleExtension = {}
        self.assertEqual(sec.capacity, initial_capacity)
        #   Check that multiplier works
        options.class_cap_multiplier = str(mult_test)
        options.save()
        sec.parent_program._moduleExtension = {}
        self.assertEqual(sec.capacity, int(initial_capacity * mult_test))
        #   Check that multiplier and offset work
        options.class_cap_offset = offset_test
        options.save()
        sec.parent_program._moduleExtension = {}
        self.assertEqual(sec._get_capacity(), int(initial_capacity * mult_test + offset_test))
        #   Check that offset only works
        options.class_cap_multiplier = '1.0'
        options.save()
        sec.parent_program._moduleExtension = {}
        self.assertEqual(sec.capacity, int(initial_capacity + offset_test))
        #   Check that we can go back to normal
        options.class_cap_offset = 0
        options.save()
        sec.parent_program._moduleExtension = {}
        self.assertEqual(sec.capacity, initial_capacity)


class ModuleControlTest(ProgramFrameworkTest):
    def runTest(self):
        from esp.program.models import ProgramModule
        from esp.program.modules.base import ProgramModuleObj
        from esp.program.modules.handlers.satprepmodule import SATPrepModule
    
        #   Make all default modules non-required
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        #   Pick a student and log in; fill out profile
        student = random.choice(self.students)
        self.failUnless( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        
        #   Check that the main student reg page displays as usual in the initial state.
        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertTrue('Steps for Registration' in response.content)
        
        #   Set a student module to be required and make sure we are shown it.
        sat_module = ProgramModule.objects.filter(handler='SATPrepModule')[0]
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, sat_module)
        moduleobj.__class__ = ProgramModuleObj
        moduleobj.required = True
        moduleobj.save()
        
        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertTrue('SAT Math Score' in response.content)
        
        #   Remove the module and make sure we are not shown it anymore.
        self.program.program_modules.remove(sat_module)
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
        self.schedule_randomly()
        self.timeslots = Event.objects.filter(meeting_times__parent_class__parent_program = self.program).distinct()

        # Create the registration types
        self.enrolled_rt, created = RegistrationType.objects.get_or_create(name='Enrolled')
        self.priority_rt, created = RegistrationType.objects.get_or_create(name='Priority/1')
        self.interested_rt, created = RegistrationType.objects.get_or_create(name='Interested')
        self.waitlist_rt, created = RegistrationType.objects.get_or_create(name='Waitlist/1')

        # Add some priorities and interesteds for the lottery
        es = Event.objects.filter(anchor=self.program.anchor)
        for student in self.students:
            # Give the student a starting grade
            startGrade = int(random.random() * 6) + 7
            student_studentinfo = StudentInfo(user=student, graduation_year=ESPUser.YOGFromGrade(startGrade))
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

    def testLottery(self):
        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()
        

        # Now go through and check that the assignments make sense
        for student in self.students:
            # Figure out which classes they got
            interested_regs = StudentRegistration.objects.filter(user=student, relationship=self.interested_rt)
            priority_regs = StudentRegistration.objects.filter(user=student, relationship=self.priority_rt)
            enrolled_regs = StudentRegistration.objects.filter(user=student, relationship=self.enrolled_rt)

            interested_classes = set([sr.section for sr in interested_regs])
            priority_classes = set([sr.section for sr in priority_regs])
            enrolled_classes = set([sr.section for sr in enrolled_regs])
            not_enrolled_classes = (priority_classes | interested_classes) - enrolled_classes


            # Get their grade
            grade = ESPUser.gradeFromYOG(student.studentinfo_set.all()[0].graduation_year)

            # Check that they can't possibly add a class they didn't get into
            for cls in not_enrolled_classes:
                self.failUnless(cls.cannotAdd(student) or cls.isFull())

    def testSingleLunchConstraint(self):
        # First generate 1 lunch timeslot
        lunch_timeslot = random.choice(self.timeslots)
        lcg = LunchConstraintGenerator(self.program, [lunch_timeslot])
        lcg.generate_all_constraints()

        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and make sure that lunch assignments make sense
        for student in self.students:
            lunch_sec = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
            self.failUnless(len(lunch_sec) == 1, "Lunch constraint for one timeblock generated multiple Lunch sections")
            lunch_sec = lunch_sec[0]
            timeslots = Event.objects.filter(meeting_times__registrations=student).exclude(meeting_times=lunch_sec)

            self.failUnless(not lunch_sec.meeting_times.all()[0] in timeslots, "One of the student's registrations overlaps with the lunch block")

    def testMultipleLunchConstraint(self):
        # First generate 3 lunch timeslots
        ts_copy = list(self.timeslots)[:]
        lt1 = random.choice(ts_copy)
        ts_copy.remove(lt1)
        lt2 = random.choice(ts_copy)
        ts_copy.remove(lt2)
        lt3 = random.choice(ts_copy)
        lcg = LunchConstraintGenerator(self.program, [lt1, lt2, lt3])
        lcg.generate_all_constraints()

        # Run the lottery!
        lotteryController = LotteryAssignmentController(self.program)
        lotteryController.compute_assignments()
        lotteryController.save_assignments()


        # Now go through and make sure that lunch assignments make sense
        for student in self.students:
            lunch_secs = ClassSection.objects.filter(parent_class__category = lcg.get_lunch_category())
            self.failUnless(len(lunch_secs) == 3, "Incorrect number of lunch sections created: %s" % (len(lunch_secs)))
            timeslots = Event.objects.filter(meeting_times__registrations=student).exclude(meeting_times__in=lunch_secs)

            lunch_free = False
            for lunch_section in lunch_secs:
                if not lunch_section.meeting_times.all()[0] in timeslots:
                    lunch_free = True
                    break
            self.failUnless(lunch_free, "No lunch sections free for a student!")
