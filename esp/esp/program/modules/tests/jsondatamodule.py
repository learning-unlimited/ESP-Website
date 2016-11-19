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

import json

from django.utils.html import escape

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.models import ClassSubject

class JSONDataModuleTest(ProgramFrameworkTest):
    ## This test is very incomplete.
    ## It needs more data, more interesting state in the program in question.
    ## It also needs all of the queries in self.program.students() and
    ## self.program.teachers() to have their own tests for correctness;
    ## at the moment it just assumes that they are correct.
    ## It also also needs to test all the other queries on this page.

    def setUp(self):
        super(JSONDataModuleTest, self).setUp()
        # Generate some nonzero stats
        self.schedule_randomly()
        self.add_user_profiles()
        self.classreg_students()

        self.pm = ProgramModule.objects.get(handler='AdminCore')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, self.pm)
        self.moduleobj.user = self.students[0]

        self.client.login(username=self.admins[0].username, password='password')
        self.stats_response = self.client.get('/json/%s/stats'
                                              % self.program.getUrlBase())
        self.classes_response = self.client.get('/json/%s/class_subjects'
                                                % self.program.getUrlBase())

    def testStudentStats(self):
        ## Student statistics
        student_labels_dict = {}
        for module in self.program.getModules():
            student_labels_dict.update(module.studentDesc())
        students_dict = self.program.students()
        student_display_dict = {}
        for key in students_dict.iterkeys():
            student_display_dict[student_labels_dict.get(key, key)] = students_dict[key]

        for query_label, query in student_display_dict.iteritems():
            value = query.count()
            json_str = "[\"%s\", %d]" % (query_label, value)
            self.assertContains(self.stats_response, json_str)

    def testTeacherStats(self):
        ## Teacher statistics
        teacher_labels_dict = {}
        for module in self.program.getModules():
            teacher_labels_dict.update(module.teacherDesc())
        teachers_dict = self.program.teachers()
        teacher_display_dict = {}
        for key in teachers_dict.iterkeys():
            teacher_display_dict[teacher_labels_dict.get(key, key)] = teachers_dict[key]

        for query_label, query in teacher_display_dict.iteritems():
            value = query.count()
            json_str = "[\"%s\", %d]" % (query_label, value)
            self.assertContains(self.stats_response, json_str)

    def testGradesStats(self):
        ## Statistics in the "grades" section of the dashboard
        ## Note: Depends on add_user_profiles() always creating 10th graders
        ## and all classes being open to all grades in the program
        expected_response = {"data": [], "id": "grades"}
        for g in xrange(self.program.grade_min, self.program.grade_max + 1):
            expected_response["data"].append({"grade": g,
                                              "num_subjects": 10,
                                              "num_sections": 10,
                                              "num_students": 10 if g==10 else 0})
        json_str = json.dumps(expected_response)
        self.assertContains(self.stats_response, json_str)

    def testClasses(self):
        ## Make sure all classes are listed
        json_classes = json.loads(str(self.classes_response.content))
        classes = ClassSubject.objects.filter(parent_program=self.program)
        self.assertEquals(len(json_classes["classes"]), classes.count())

        json_classes_dict = dict()
        for json_cls in json_classes["classes"]:
            json_classes_dict[json_cls['id']] = json_cls
        for cls in classes:
            # Very basic check that we're getting the data correctly
            self.assertTrue(cls.id in json_classes_dict)
            self.assertEquals(json_classes_dict[cls.id]['emailcode'], cls.emailcode())
