from django.contrib.auth.models import User,Group
import datetime, random, hashlib
import unittest
from django.test import TestCase

class ProfileTest(unittest.TestCase):

    def setUp(self):
        self.salt = hashlib.sha1(str(random.random())).hexdigest()[:5]

    def testAcctCreate(self):
        self.u=User(
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
        self.assertEquals(User.objects.get(username='bjones'), self.u)
        self.assertEquals(Group.objects.get(name='Test Group'), self.group)
        print self.u.__dict__
        print self.u.groups.all()


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
        from django.db import transaction, connection
        
        # Force DataTree to work
        # FIXME: we shouldn't have to do this here!
        cursor = connection.cursor()
        transaction.enter_transaction_management()
        cursor.execute("""INSERT INTO datatree_datatree (name, friendly_name, uri, uri_correct, rangestart, rangeend, range_correct, lock_table )
            VALUES ('ROOT', '', '', TRUE, 0, 25, TRUE, 0 )""")
        transaction.commit()
        transaction.leave_transaction_management()
        
        # make program type, since we can't do that yet
        self.program_type_anchor = GetNode('Q/Programs/Prubbogrubbam')
        self.program_type_anchor.friendly_name = u'Prubbogrubbam!'
        self.program_type_anchor.save()
        
        def makeuser(f, l, un, email, p):
            u = User(first_name=f, last_name=l, username=un, email=email)
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
            main_call='listclasses', aux_calls='class_students,section_students,makeaclass,editclass,deleteclass,coteachers,teacherlookup,class_status,class_docs,select_students',
            seq=10, required=False)
        ProgramModule.objects.create(link_title='Sign up for Classes', admin_title='Student Class Registration', module_type='learn', handler='StudentClassRegModule',
            main_call='classlist', aux_calls='catalog,clearslot,fillslot,changeslot,addclass,swapclass,class_docs',
            seq=10, required=True)
        ProgramModule.objects.create(link_title='Sign up for a Program', admin_title='Student Registration Core', module_type='learn', handler='StudentRegCore',
            main_call='studentreg', aux_calls='confirmreg,cancelreg',
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
        from datetime import datetime
        
        timeslot_type = EventType.objects.create(description='Class Time Block')
        self.timeslot = Event.objects.create(anchor=self.prog.anchor, description='Never', short_description='Never Ever',
            start=datetime(3001,1,1,12,0), end=datetime(3001,1,1,13,0), event_type=timeslot_type )
        classroom_type = ResourceType.objects.create(name='Classroom', consumable=False, priority_default=0,
            description='Each classroom or location is a resource; almost all classes need one.')
        self.classroom = Resource.objects.create(name='Nowhere', num_students=50, res_type=classroom_type, event=self.timeslot)
        
        # Teacher logs in and posts class
        self.loginTeacher()
        class_dict = {
            'title': 'Chairing',
            'category': self.prog.class_categories.all()[0].id,
            'class_info': 'Chairing is fun!',
            'prereqs': 'A chair.',
            'duration': self.prog.getDurations()[0][0],
            'num_sections': '1',
            'session_count': '1',
            'grade_min': self.prog.grade_min,
            'grade_max': self.prog.grade_max,
            'class_size_max': '10',
            'allow_lateness': 'False',
            'has_own_space': 'False',
            'requested_special_resources': 'Two doorstops and a first-aid kit.',
            'message_for_directors': 'Hi chairs!',
            
            'class_reg_page': '1'
        }
        self.client.post('%smakeaclass' % self.prog.get_teach_url(), class_dict)
        
        # Check that stuff went through correctly
        classes = self.prog.classes()
        self.failUnless( classes.count() == 1 )
        self.classsubject = classes[0]
        self.assertEqual( unicode(self.classsubject.title()), unicode(class_dict['title']), 'Failed to save title.' )
    
    def studentreg(self):
        from esp.users.models import ContactInfo, StudentInfo, UserBit
        from esp.program.models import RegistrationProfile
        from datetime import datetime, timedelta
        
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
        self.assertTrue( UserBit.UserHasPerms(user=self.student, qsc=sec.anchor,
            verb=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb), 'Registration failed.')
        
        # Try dropping a class.
        self.client.get('%sclearslot/%s' % (self.prog.get_learn_url(), self.timeslot.id))
        self.assertFalse( UserBit.UserHasPerms(user=self.student, qsc=sec.anchor,
            verb=self.prog.getModuleExtension('StudentClassRegModuleInfo').signup_verb), 'Registration failed.')
        
        pass
    
    def runTest(self):
        self.makeprogram()
        self.teacherreg()
        self.studentreg()
