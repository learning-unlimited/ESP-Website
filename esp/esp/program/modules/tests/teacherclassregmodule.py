__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

import random

from django.db import transaction

from esp.cal.models import Event
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.models import ClassSubject, RegistrationType
from esp.program.setup import prepare_program, commit_program
from esp.program.forms import ProgramCreationForm
from esp.resources.models import ResourceType, ResourceRequest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, Permission

class TeacherClassRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(TeacherClassRegTest, self).setUp(num_students=5, room_capacity=5, *args, **kwargs)

        # Select a primary teacher, two other teachers, and the class
        self.teacher = random.choice(self.teachers)
        self.cls = random.choice(self.teacher.getTaughtClasses())
        other_teachers = list(self.teachers)
        other_teachers.remove(self.teacher)
        self.other_teacher1 = random.choice(other_teachers)
        other_teachers.remove(self.other_teacher1)
        self.other_teacher2 = random.choice(other_teachers)

        self.free_teacher1, created = ESPUser.objects.get_or_create(
            username='freeteacher1',
            first_name='Free',
            last_name='Teacher1',
            email='freeteacher1@example.com')
        self.free_teacher1.set_password('password')
        self.free_teacher1.save()
        self.free_teacher2, created = ESPUser.objects.get_or_create(
            username='freeteacher2',
            first_name='Free',
            last_name='Teacher2',
            email='freeteacher2@example.com')
        self.free_teacher2.set_password('password')
        self.free_teacher2.save()

        # Make the teachers available all the time
        for ts in self.program.getTimeSlots():
            self.free_teacher1.addAvailableTime(self.program, ts)
            self.free_teacher2.addAvailableTime(self.program, ts)
        # Make the primary teacher an admin of the class

        # Get and remember the instance of TeacherClassRegModule
        pm = ProgramModule.objects.get(handler='TeacherClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.teacher

    def test_grade_range_popup(self):
        # Login the teacher
        self.assertTrue(self.client.login(username=self.teacher.username, password='password'), "Couldn't log in as teacher %s" % self.teacher.username)

        # Try editing the class
        response = self.client.get('%smakeaclass' % self.program.get_teach_url())
        self.assertTrue("check_grade_range" in response.content)

        # Add a tag that specifically removes this functionality
        Tag.setTag('grade_range_popup', self.program, 'False')

        # Try editing the class
        response = self.client.get('%smakeaclass' % self.program.get_teach_url())
        self.assertTrue(not "check_grade_range" in response.content)

    def apply_coteacher_op(self, dict):
        return self.client.post('%scoteachers' % self.program.get_teach_url(), dict)

    def has_coteacher(self, teacher, response):
        return "(" + teacher.username + ")" in response

    def test_adding_coteachers(self):
        # Login the teacher
        self.assertTrue(self.client.login(username=self.teacher.username, password='password'), "Couldn't log in as teacher %s" % self.teacher.username)

        cur_coteachers = []

        # Error on adding self
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.teacher.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.assertTrue("Error" in response.content)

        # Error on no teacher selected
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': '', 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue("Error" in response.content)

        # Add free_teacher1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.free_teacher1.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(self.has_coteacher(self.free_teacher1, response.content))
        cur_coteachers.append(self.free_teacher1.id)

        # Error on adding the same coteacher again
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.free_teacher1.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue("Error" in response.content)

        # Add free_teacher2
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.free_teacher2.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(self.has_coteacher(self.free_teacher2, response.content))
        cur_coteachers.append(self.free_teacher2.id)

        # Delete free_teacher 1
        response = self.apply_coteacher_op({'op': 'del', 'clsid': self.cls.id, 'delete_coteachers': self.free_teacher1.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(not self.has_coteacher(self.free_teacher1, response.content))
        cur_coteachers.remove(self.free_teacher1.id)

        # Add free_teacher 1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.free_teacher1.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(self.has_coteacher(self.free_teacher1, response.content))
        cur_coteachers.append(self.free_teacher1.id)

        # Delete both free_teacher1 and free_teacher2
        response = self.apply_coteacher_op({'op': 'del', 'clsid': self.cls.id, 'delete_coteachers': [self.free_teacher1.id, self.free_teacher2.id], 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(not self.has_coteacher(self.free_teacher1, response.content) and not self.has_coteacher(self.free_teacher2, response.content))
        cur_coteachers.remove(self.free_teacher1.id)
        cur_coteachers.remove(self.free_teacher2.id)

        # Add free_teacher 1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.free_teacher1.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(self.has_coteacher(self.free_teacher1, response.content))
        cur_coteachers.append(self.free_teacher1.id)

        # Save the coteachers
        self.apply_coteacher_op({'op': 'save', 'clsid': self.cls.id, 'coteachers': ",".join([str(coteacher) for coteacher in cur_coteachers])})
        self.assertTrue(self.cls in self.teacher.getTaughtClasses())
        self.assertTrue(self.cls in self.free_teacher1.getTaughtClasses())
        self.assertTrue(not self.cls in self.free_teacher2.getTaughtClasses())

    def add_resource_request(self, sec, res_type, val):
        rr = ResourceRequest()
        rr.target = sec
        rr.res_type = res_type
        rr.desired_value = val
        rr.save()

    def delete_resource_request(self, sec, res_type):
        ResourceRequest.objects.filter(target = sec, res_type = res_type).delete()

    def has_resource_pair_with_teacher(self, res_type, val_index, teacher):
        label = 'teacher_res_%d_%d' % (res_type.id, val_index)
        label_list = [resource_pair[0] for resource_pair in self.moduleobj.get_resource_pairs()]
        if not label in label_list:
            return False
        i = label_list.index(label)
        teacher_list = ESPUser.objects.filter(self.moduleobj.get_resource_pairs()[i][2])
        return teacher in teacher_list

    @transaction.atomic
    def test_get_resource_pairs(self):
        prog = self.program
        new_res_type1 = ResourceType.get_or_create('NewResource1', program = self.program)
        new_res_type2 = ResourceType.get_or_create('NewResource2', program = self.program)
        sec = random.choice(self.cls.sections.all())

        self.add_resource_request(sec, new_res_type1, 'Yes')
        self.assertTrue(self.has_resource_pair_with_teacher(new_res_type1, 0, self.teacher))

        self.add_resource_request(sec, new_res_type2, 'ThisValueIsAwesome')
        self.assertTrue(self.has_resource_pair_with_teacher(new_res_type2, 0, self.teacher))

        self.delete_resource_request(sec, new_res_type1)
        self.assertTrue(not self.has_resource_pair_with_teacher(new_res_type1, 0, self.teacher))


    def check_all_teachers(self, all_teachers):
        teaching_teachers = [teacher for teacher in self.teachers
                                     if len(teacher.getTaughtClasses()) > 0]
        return set(teaching_teachers) == set(all_teachers)

    @transaction.atomic
    def test_teachers(self):
        # Get the instance of StudentClassRegModule
        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        ProgramModuleObj.getFromProgModule(self.program, pm)

        d = self.moduleobj.teachers()

        # Reject a class from self.teacher, approve a class from self.other_teacher1, make a class from self.other_teacher2 proposed
        cls1 = random.choice(self.teacher.getTaughtClasses())
        cls1.status = -1
        cls1.save()
        cls2 = random.choice(self.other_teacher1.getTaughtClasses())
        cls2.status = 1
        cls2.save()
        cls3 = random.choice(self.other_teacher2.getTaughtClasses())
        cls3.status = 0
        cls3.save()
        # Check them
        d = self.moduleobj.teachers()
        self.assertTrue(self.teacher in d['class_rejected'])
        self.assertTrue(self.other_teacher1 in d['class_approved'])
        self.assertTrue(self.other_teacher2 in d['class_proposed'])
        # Undo the statuses
        cls1.status = 10
        cls1.save()
        cls2.status = 10
        cls2.save()
        cls3.status = 10
        cls3.save()

        # Schedule the classes randomly
        self.schedule_randomly()
        # Find an empty class
        cls = random.choice([cls for cls in self.program.classes() if not cls.isFull() and not cls.is_nearly_full(ClassSubject.get_capacity_factor())])
        teacher = cls.get_teachers()[0]
        classes = list(teacher.getTaughtClasses())
        classes.remove(cls)
        for c in classes:
            c.removeTeacher(teacher)
        d = self.moduleobj.teachers()
        # Check it
        self.assertTrue(teacher not in d['class_full'] and teacher not in d['class_nearly_full'])

        # Mostly fill it
        self.add_student_profiles()
        for i in range(0, 4):
            cur_student = self.students[i]
            cls.preregister_student(cur_student)
        # Check it
        d = self.moduleobj.teachers()
        self.assertTrue(teacher in d['class_nearly_full'])
        self.assertTrue(teacher not in d['class_full'])

        # Fill it
        cls.get_sections()[0].preregister_student(self.students[4])
        # Check it
        d = self.moduleobj.teachers()
        self.assertTrue(teacher in d['class_full'])
        self.assertTrue(teacher in d['class_nearly_full'])

        # Make a program
        self.create_past_program()

        # Create a class for the teacher
        new_class, created = ClassSubject.objects.get_or_create(category=self.categories[0], grade_min=7, grade_max=12, parent_program=self.new_prog, class_size_max=30, class_info='Previous class!')
        new_class.makeTeacher(self.teacher)
        new_class.add_section(duration=50.0/60.0)
        new_class.accept()
        # Check taught_before
        d = self.moduleobj.teachers()
        self.assertTrue(self.teacher in d['taught_before'])

    @transaction.atomic
    def test_deadline_met(self):

        self.assertTrue(self.moduleobj.deadline_met())
        self.moduleobj.user = self.teachers[0]
        self.assertTrue(self.moduleobj.deadline_met())

        Permission.objects.filter(permission_type__startswith='Teacher', program=self.moduleobj.program).delete()

        self.assertTrue(not self.moduleobj.deadline_met())
        self.moduleobj.user = self.teacher
        self.assertTrue(not self.moduleobj.deadline_met())
