from __future__ import absolute_import
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
        for key in six.iterkeys(students_dict):
            if key not in ['attended_past', 'enrolled_past']:
                student_display_dict[student_labels_dict.get(key, key)] = students_dict[key]

        for query_label, query in six.iteritems(student_display_dict):
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
        for key in six.iterkeys(teachers_dict):
            if key not in ['taught_before']:
                teacher_display_dict[teacher_labels_dict.get(key, key)] = teachers_dict[key]

        for query_label, query in six.iteritems(teacher_display_dict):
            value = query.count()
            json_str = "[\"%s\", %d]" % (query_label, value)
            self.assertContains(self.stats_response, json_str)

    def testGradesStats(self):
        ## Statistics in the "grades" section of the dashboard
        ## Note: Depends on add_user_profiles() always creating 10th graders
        ## and all classes being open to all grades in the program
        expected_response = {"data": [], "id": "grades"}
        for g in range(self.program.grade_min, self.program.grade_max + 1):
            expected_response["data"].append({"grade": g,
                                              "num_subjects": 10,
                                              "num_sections": 10,
                                              "num_students": 10 if g==10 else 0})
        self.assertContains(self.stats_response, 'stats', status_code=200)
        self.assertIn('stats', list(self.stats_response.json().keys()))
        grades_count = 0
        for res in self.stats_response.json()['stats']:
            self.assertIn('id', list(res.keys()))
            if res['id'] == 'grades':
                grades_count += 1
                self.assertJSONEqual(json.dumps(res), expected_response)
        self.assertEqual(grades_count, 1)

    def testClasses(self):
        ## Make sure all classes are listed
        json_classes = self.classes_response.json()
        classes = ClassSubject.objects.filter(parent_program=self.program)
        self.assertEquals(len(json_classes["classes"]), classes.count())

        json_classes_dict = dict()
        for json_cls in json_classes["classes"]:
            json_classes_dict[json_cls['id']] = json_cls
        for cls in classes:
            # Very basic check that we're getting the data correctly
            self.assertTrue(cls.id in json_classes_dict)
            self.assertEquals(json_classes_dict[cls.id]['emailcode'], cls.emailcode())

    # ------------------------------------------------------------------
    # Additional tests for issue #599: Dashboard stats JSON interface
    # ------------------------------------------------------------------

    def testStatsResponseStructure(self):
        """The /json/.../stats endpoint returns a dict with a 'stats' list."""
        self.assertEqual(self.stats_response.status_code, 200)
        data = self.stats_response.json()
        self.assertIn('stats', data)
        self.assertIsInstance(data['stats'], list)
        ids = [s['id'] for s in data['stats'] if 'id' in s]
        for expected_id in ('vitals', 'shirtnum', 'categories', 'grades', 'accounting'):
            self.assertIn(expected_id, ids,
                          "'%s' section missing from stats response" % expected_id)

    def testVitalsSection(self):
        """The 'vitals' section contains non-negative integer counts."""
        stats = self.stats_response.json()['stats']
        vitals = next(s for s in stats if s.get('id') == 'vitals')
        for field in ('classnum', 'teachernum', 'studentnum', 'volunteernum', 'hournum'):
            self.assertIn(field, vitals, "vitals missing field '%s'" % field)

    def testClassNums(self):
        """Class counts in vitals match what's in the database."""
        from esp.program.models import ClassSubject
        stats = self.stats_response.json()['stats']
        vitals = next(s for s in stats if s.get('id') == 'vitals')
        total_classes = ClassSubject.objects.filter(
            parent_program=self.program).count()
        # classnum is a list of (label, count) pairs; total is the first entry
        classnum = vitals['classnum']
        self.assertIsInstance(classnum, list)
        self.assertGreater(len(classnum), 0)
        # First entry is ("Total # of Classes", N)
        self.assertEqual(classnum[0][1], total_classes)

    def testCategoriesSection(self):
        """The 'categories' section lists per-category stats."""
        stats = self.stats_response.json()['stats']
        cats = next(s for s in stats if s.get('id') == 'categories')
        self.assertIn('data', cats)
        self.assertIsInstance(cats['data'], list)
        if cats['data']:
            entry = cats['data'][0]
            for field in ('id', 'category', 'num_subjects', 'num_sections', 'num_class_hours'):
                self.assertIn(field, entry,
                              "categories entry missing field '%s'" % field)

    def testAccountingSection(self):
        """The 'accounting' section contains payment totals."""
        stats = self.stats_response.json()['stats']
        acct = next(s for s in stats if s.get('id') == 'accounting')
        self.assertIn('data', acct)
        data = acct['data']
        self.assertIn('num_payments', data)
        self.assertIn('total_payments', data)
        self.assertIsInstance(data['num_payments'], int)
        self.assertIsInstance(data['total_payments'], float)

    def testStatsRequiresAdmin(self):
        """The /json/.../stats endpoint requires an admin login."""
        from django.test import Client
        anon_client = Client()
        url = '/json/%s/stats' % self.program.getUrlBase()
        response = anon_client.get(url)
        # Should redirect to login or return 403, not 200
        self.assertNotEqual(response.status_code, 200)

    def testClassSubjectsFields(self):
        """Every class in class_subjects has the required fields."""
        json_classes = self.classes_response.json()
        self.assertIn('classes', json_classes)
        required_fields = ('id', 'status', 'title', 'category', 'category_id',
                           'class_size_max', 'grade_min', 'grade_max',
                           'emailcode', 'sections', 'teachers')
        for cls_data in json_classes['classes']:
            for field in required_fields:
                self.assertIn(field, cls_data,
                              "class_subjects entry missing field '%s'" % field)

    def testClassSubjectsSectionsAreLists(self):
        """The 'sections' field in each class_subjects entry is a list of ints."""
        json_classes = self.classes_response.json()
        for cls_data in json_classes['classes']:
            self.assertIsInstance(cls_data['sections'], list)

    def testClassSubjectsTeachersAreListed(self):
        """Teachers are included in class_subjects and match actual teacher IDs."""
        json_classes = self.classes_response.json()
        for cls_data in json_classes['classes']:
            self.assertIsInstance(cls_data['teachers'], list)

    def testClassSubjectsTeachersBlock(self):
        """The top-level 'teachers' block in class_subjects has correct fields."""
        json_classes = self.classes_response.json()
        self.assertIn('teachers', json_classes)
        for t in json_classes['teachers']:
            for field in ('id', 'username', 'first_name', 'last_name', 'sections'):
                self.assertIn(field, t,
                              "teachers entry missing field '%s'" % field)

    def testClassSubjectsCatalogMode(self):
        """Catalog mode includes extra fields (class_info, prereqs, difficulty)."""
        url = '/json/%s/class_subjects/catalog' % self.program.getUrlBase()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_classes = response.json()
        for cls_data in json_classes['classes']:
            for field in ('class_info', 'prereqs', 'difficulty'):
                self.assertIn(field, cls_data,
                              "catalog mode missing field '%s'" % field)

    def testClassSubjectsGradeRange(self):
        """grade_min and grade_max in class_subjects are within the program range."""
        json_classes = self.classes_response.json()
        prog_min = self.program.grade_min
        prog_max = self.program.grade_max
        for cls_data in json_classes['classes']:
            self.assertGreaterEqual(cls_data['grade_max'], cls_data['grade_min'])
            self.assertGreaterEqual(cls_data['grade_min'], prog_min)
            self.assertLessEqual(cls_data['grade_max'], prog_max)

