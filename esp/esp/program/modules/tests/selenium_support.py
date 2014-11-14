from esp.users.models import Permission
from esp.users.models import ESPUser
from esp.program.models import ClassSubject, ClassSection, RegistrationProfile, ScheduleMap, ProgramModule, StudentRegistration, RegistrationType, Event, ClassCategories
from esp.resources.models import ResourceType

from django.contrib.auth.models import User, Group
from django.test import LiveServerTestCase

from django.test import LiveServerTestCase
from esp.tests.util import user_role_setup

import re
import unicodedata

class ProgramFrameworkSeleniumTest(LiveServerTestCase):
    """ A test case that initializes a program with the parameters passed to setUp(). 
        Everything is done with get_or_create so it can be run multiple times in the
        same session.
        
        This is intended to facilitate the writing of unit tests for program modules
        and other functions that deal with program-specific data.  Once the setUp()
        function is called, you can use self.students, self.teachers, self.program
        and the settings.
    """
    
    def setUp(self, *args, **kwargs):
        from esp.cal.models import Event, EventType
        from esp.cal.models import install as cal_install
        from esp.resources.models import Resource, ResourceType
        from esp.program.setup import prepare_program, commit_program
        from esp.program.forms import ProgramCreationForm
        from esp.qsd.models import QuasiStaticData
        from esp.web.models import NavBarCategory
        from datetime import datetime, timedelta
        from esp.program.modules.models import install as program_modules_install

        user_role_setup()
        program_modules_install()
        cal_install()
        
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
                    'modules':[x.id for x in ProgramModule.objects.all()],
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
            new_student, created = ESPUser.objects.get_or_create(username='student%04d' % i)
            new_student.set_password('password')
            new_student.save()
            new_student.makeRole("Student")
            self.students.append(ESPUser(new_student)) 
        for i in range(settings['num_teachers']):
            new_teacher, created = ESPUser.objects.get_or_create(username='teacher%04d' % i)
            new_teacher.set_password('password')
            new_teacher.save()
            new_teacher.makeRole("Teacher")
            self.teachers.append(ESPUser(new_teacher))
        for i in range(settings['num_admins']):
            new_admin, created = ESPUser.objects.get_or_create(username='admin%04d' % i)
            new_admin.set_password('password')
            new_admin.save()
            new_admin.makeRole("Administrator")
            self.admins.append(ESPUser(new_admin))
            
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
            print "ProgramCreationForm errors"
            print pcf.data
            print pcf.errors
            print prog_form_values
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
        
        commit_program(new_prog, perms, modules, pcf.cleaned_data['base_cost'])

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
                                              nav_category=NavBarCategory.objects.get_or_create(name="learn", long_explanation="")[0])
