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
  Email: web-team@lists.learningu.org
"""

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.tagdict.models import Tag
import random

class TeacherClassRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(TeacherClassRegTest, self).setUp(*args, **kwargs)

        # Select a primary teacher, two other teachers, and the class
        self.teacher = random.choice(self.teachers)
        self.cls = random.choice(self.teacher.getTaughtClasses())
        other_teachers = self.teachers
        other_teachers.remove(self.teacher)
        self.other_teacher1 = random.choice(other_teachers)
        other_teachers.remove(self.other_teacher1)
        self.other_teacher2 = random.choice(other_teachers)

        #pm = ProgramModule.objects.get(handler='TeacherClassRegModule')
        #self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        #self.moduleobj.user = self.teacher

    def test_grade_range_popup(self):
        # Login the teacher
        self.failUnless(self.client.login(username=self.teacher.username, password='password'), "Couldn't log in as teacher %s" % self.teacher.username)

        # Try editing the class
        response = self.client.get('%smakeaclass' % self.program.get_teach_url())
        self.failUnless("check_grade_range" in response.content)

        # Add a tag that specifically removes this functionality
        Tag.setTag('grade_range_popup', self.program, 'False')

        # Try editing the class
        response = self.client.get('%smakeaclass' % self.program.get_teach_url())
        self.failUnless(not "check_grade_range" in response.content)

        # Change the grade range of the program and reset the tag
        self.program.grade_min = 7
        self.program.grade_max = 8
        self.program.save()
        Tag.setTag('grade_range_popup', self.program, 'True')

        # Try editing the class
        response = self.client.get('%smakeaclass' % self.program.get_teach_url())
        self.failUnless(not "check_grade_range" in response.content)

    def apply_coteacher_op(self, dict):
        return self.client.post('%scoteachers' % self.program.get_teach_url(), dict)

    def has_coteacher(self, teacher):
        return teacher.first_name + ", " + teacher.last_name in response.content

    def test_adding_coteachers(self):
        # Login the teacher
        self.failUnless(self.client.login(username=self.teacher.username, password='password'), "Couldn't log in as teacher %s" % self.teacher.username)

        cur_coteachers = []

        # Error on adding self
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.teacher.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless("Error" in response.content)

        # Error on no teacher selected
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': '', 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless("Error" in response.content)

        # Add other_teacher1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.other_teacher1.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(has_coteacher(self.other_teacher1))
        cur_coteachers.append(self.other_teacher1.id)

        # Error on adding the same coteacher again
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.other_teacher1.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless("Error" in response.content)

        # Add other_teacher2
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.other_teacher2.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(has_coteacher(self.other_teacher2))
        cur_coteachers.append(self.other_teacher2.id)

        # Delete other_teacher 1
        response = self.apply_coteacher_op({'op': 'delete', 'clsid': self.cls.id, 'delete_coteachers': self.other_teacher1.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(not has_coteacher(self.other_teacher1))
        cur_coteachers.remove(self.other_teacher1.id)

        # Add other_teacher 1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.other_teacher1.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(has_coteacher(self.other_teacher1))
        cur_coteachers.append(self.other_teacher1.id)

        # Delete both other_teacher1 and other_teacher2
        response = self.apply_coteacher_op({'op': 'delete', 'clsid': self.cls.id, 'delete_coteachers': [self.other_teacher1.id, self.other_teacher2.id].join(","), 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(not has_coteacher(self.other_teacher1) and not has_coteacher(self.other_teacher2))
        cur_coteachers.remove(self.other_teacher1.id)
        cur_coteachers.remove(self.other_teacher2.id)

        # Add other_teacher 1
        response = self.apply_coteacher_op({'op': 'add', 'clsid': self.cls.id, 'teacher_selected': self.other_teacher1.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(has_coteacher(self.other_teacher1))
        cur_coteachers.append(self.other_teacher1.id)

        # Save the coteachers
        self.apply_coteacher_op({'op': 'save', 'clsid': self.cls.id, 'coteachers': ",".join([str(coteacher.id) for coteacher in cur_coteachers])})
        self.failUnless(self.cls in self.teacher.getTaughtClasses())
        self.failUnless(self.cls in self.other_teacher1.getTaughtClasses())
        self.failUnless(not self.cls in self.other_teacher2.getTaughtClasses())

