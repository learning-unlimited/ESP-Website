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
from collections import Counter

from django.utils.html import escape

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.models import ClassSubject
from esp.resources.models import ResourceType

class JSONDataModuleTest(ProgramFrameworkTest):
    ## This test is very incomplete.
    ## It needs more data, more interesting state in the program in question.
    ## It also needs all of the queries in self.program.students() and
    ## self.program.teachers() to have their own tests for correctness;
    ## at the moment it just assumes that they are correct.
    ## It also also needs to test all the other queries on this page.

    @classmethod
    def setUpTestData(cls):
        """Run all heavy DB setup once at the class level.

        Django wraps this in a transaction savepoint that is shared by every
        test method in the class and rolled back when the class finishes.
        This avoids repeating the expensive program-framework scaffolding
        (user creation, class scheduling, student registration) on every
        individual test method.
        """
        super().setUpTestData()
        # Bootstrap the program framework at the class level.  We invoke each
        # instance method explicitly with `cls` as the receiver so that Python
        # binds the class object as `self`.  ProgramFrameworkTest.setUp only
        # performs DB writes (no HTTP client usage), so this is safe.
        ProgramFrameworkTest.setUp(cls)
        ProgramFrameworkTest.schedule_randomly(cls)
        ProgramFrameworkTest.add_user_profiles(cls)
        ProgramFrameworkTest.classreg_students(cls)

    def setUp(self):
        # We deliberately do NOT call super().setUp() here.  ProgramFrameworkTest
        # mixes two concerns in its setUp: (a) expensive one-time DB scaffolding
        # (program creation, user creation, etc.) which was already done once at
        # the class level in setUpTestData, and (b) lightweight per-test state
        # resets.  Calling super().setUp() per-test would re-run the full program
        # creation form, which fails because the program already exists.
        #
        # We therefore replicate only the per-test isolation steps from
        # ProgramFrameworkTest.setUp explicitly:
        #   1. Reset the in-memory ResourceType cache so stale entries from one
        #      test can't pollute the next (ProgramFrameworkTest.setUp line ~527).
        #   2. No other shared mutable state is mutated by ProgramFrameworkTest.setUp.
        #
        # This preserves test isolation without the O(N) per-test DB overhead.
        ResourceType._get_or_create_cache = {}
        self.pm = ProgramModule.objects.get(handler='AdminCore')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, self.pm)
        self.moduleobj.user = self.students[0]

        self.client.login(username=self.admins[0].username, password='password')
        self.stats_response = self.client.get('/json/%s/stats'
                                              % self.program.getUrlBase())
        self.classes_response = self.client.get('/json/%s/class_subjects'
                                                % self.program.getUrlBase())
        # Ensure endpoints returned successfully before attempting to parse JSON.
        self.assertEqual(
            self.stats_response.status_code, 200,
            "Expected 200 from /json/%s/stats, got %d. Body snippet: %r"
            % (self.program.getUrlBase(),
               self.stats_response.status_code,
               self.stats_response.content[:200]),
        )
        self.assertEqual(
            self.classes_response.status_code, 200,
            "Expected 200 from /json/%s/class_subjects, got %d. Body snippet: %r"
            % (self.program.getUrlBase(),
               self.classes_response.status_code,
               self.classes_response.content[:200]),
        )
        # Cache parsed payloads so individual tests don't re-parse repeatedly.
        try:
            self.stats_data = self.stats_response.json()
        except ValueError:
            self.fail(
                "Failed to parse JSON from /json/%s/stats (status %d). "
                "Body snippet: %r"
                % (self.program.getUrlBase(),
                   self.stats_response.status_code,
                   self.stats_response.content[:200])
            )
        try:
            self.classes_data = self.classes_response.json()
        except ValueError:
            self.fail(
                "Failed to parse JSON from /json/%s/class_subjects (status %d). "
                "Body snippet: %r"
                % (self.program.getUrlBase(),
                   self.classes_response.status_code,
                   self.classes_response.content[:200])
            )

    def testStudentStats(self):
        ## Student statistics
        student_labels_dict = {}
        for module in self.program.getModules():
            student_labels_dict.update(module.studentDesc())
        students_dict = self.program.students()
        student_display_dict = {}
        for key in students_dict.keys():
            if key not in ['attended_past', 'enrolled_past']:
                student_display_dict[student_labels_dict.get(key, key)] = students_dict[key]

        for query_label, query in student_display_dict.items():
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
        for key in teachers_dict.keys():
            if key not in ['taught_before']:
                teacher_display_dict[teacher_labels_dict.get(key, key)] = teachers_dict[key]

        for query_label, query in teacher_display_dict.items():
            value = query.count()
            json_str = "[\"%s\", %d]" % (query_label, value)
            self.assertContains(self.stats_response, json_str)

    def testGradesStats(self):
        ## Statistics in the "grades" section of the dashboard
        ## Note: Depends on add_user_profiles() always creating 10th graders
        ## and all classes being open to all grades in the program

        # Derive expected counts dynamically from the live program data so
        # that the assertion doesn't break when the test-framework defaults
        # (num_teachers, classes_per_teacher, sections_per_class) change.
        all_classes = self.program.classes().filter(status__gte=0)
        all_sections = self.program.sections().filter(status__gte=0)

        # Pre-fetch grade ranges and parent-class IDs in exactly two flat
        # queries, then compute per-grade counts in Python.  This avoids the
        # O(grades) query overhead of calling .count() twice per grade.
        class_grade_ranges = list(
            all_classes.values_list('id', 'grade_min', 'grade_max')
        )
        section_class_ids = list(
            all_sections.values_list('parent_class_id', flat=True)
        )
        sections_per_class = Counter(section_class_ids)

        expected_response = {"data": [], "id": "grades"}
        for g in range(self.program.grade_min, self.program.grade_max + 1):
            grade_class_ids = [
                cid for cid, gmin, gmax in class_grade_ranges
                if gmin <= g <= gmax
            ]
            expected_response["data"].append({
                "grade": g,
                "num_subjects": len(grade_class_ids),
                "num_sections": sum(
                    sections_per_class.get(cid, 0) for cid in grade_class_ids
                ),
                "num_students": 10 if g == 10 else 0,
            })
        # Use the pre-parsed self.stats_data (cached in setUp) throughout to
        # avoid redundant JSON reparsing.
        self.assertContains(self.stats_response, 'stats', status_code=200)
        self.assertIn('stats', list(self.stats_data.keys()))
        grades_count = 0
        for res in self.stats_data['stats']:
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
        """The /json/.../stats endpoint returns a 'stats' list containing
        entries for all expected section IDs, with no duplicates, and each
        section carries a valid 'id' key.
        (200 status is already asserted in setUp.)"""
        self.assertIn('stats', self.stats_data)
        sections = self.stats_data['stats']
        # Every entry must have an 'id' key.
        for section in sections:
            self.assertIn('id', section, "A stats section is missing its 'id' key")
        ids = [s['id'] for s in sections]
        # IDs must be unique — duplicate sections would indicate a bug.
        self.assertEqual(len(ids), len(set(ids)),
                         "Duplicate section IDs in stats response: %r" % ids)
        for expected_id in ('vitals', 'shirtnum', 'categories', 'grades', 'accounting'):
            self.assertIn(expected_id, ids,
                          "'%s' section missing from stats response" % expected_id)

    def testVitalsSection(self):
        """The 'vitals' section contains the expected stat list fields."""
        vitals = next((s for s in self.stats_data['stats'] if s.get('id') == 'vitals'), None)
        self.assertIsNotNone(vitals, "'vitals' section missing from stats response")
        for field in ('classnum', 'teachernum', 'studentnum', 'volunteernum', 'hournum'):
            self.assertIn(field, vitals, "vitals missing field '%s'" % field)
            # Each of these is a list of [label, value] pairs
            self.assertIsInstance(vitals[field], list,
                                  "vitals['%s'] should be a list" % field)

    def testClassNums(self):
        """The first entry of vitals['classnum'] equals total classes in the DB."""
        vitals = next((s for s in self.stats_data['stats'] if s.get('id') == 'vitals'), None)
        self.assertIsNotNone(vitals, "'vitals' section missing from stats response")
        class_num_pairs = vitals['classnum']
        self.assertTrue(len(class_num_pairs) > 0, "vitals['classnum'] is empty")
        # The first pair is ("Total # of Classes", N)
        _label, total_count = class_num_pairs[0]
        expected = self.program.classes().distinct().count()
        self.assertEqual(total_count, expected,
                         "vitals classnum total mismatch: got %d, expected %d"
                         % (total_count, expected))

    def testCategoriesSection(self):
        """The 'categories' section has per-category data with required fields."""
        categories = next((s for s in self.stats_data['stats'] if s.get('id') == 'categories'), None)
        self.assertIsNotNone(categories, "'categories' section missing from stats response")
        self.assertIn('data', categories, "'categories' section missing 'data' key")
        for entry in categories['data']:
            for field in ('id', 'num_subjects', 'num_sections', 'num_class_hours', 'category'):
                self.assertIn(field, entry,
                              "categories entry missing field '%s'" % field)
            # num_class_hours is converted to float by the handler
            self.assertIsInstance(entry['num_class_hours'], float,
                                  "num_class_hours should be a float")

    def testAccountingSection(self):
        """The 'accounting' section contains correctly typed payment totals."""
        acct = next((s for s in self.stats_data['stats'] if s.get('id') == 'accounting'), None)
        self.assertIsNotNone(acct, "'accounting' section missing from stats response")
        self.assertIn('data', acct, "'accounting' section missing 'data' key")
        data = acct['data']
        self.assertIn('num_payments', data)
        self.assertIn('total_payments', data)
        self.assertIsInstance(data['num_payments'], int,
                              "num_payments should be an int")
        self.assertIsInstance(data['total_payments'], float,
                              "total_payments should be a float")

    def testStatsRequiresAdmin(self):
        """Unauthenticated access to /json/.../stats must return a 302 redirect
        to the login page or a 403 Forbidden — never 200."""
        self.client.logout()
        url = '/json/%s/stats' % self.program.getUrlBase()
        response = self.client.get(url)
        self.assertIn(
            response.status_code, (302, 403),
            "stats endpoint should redirect (302) or forbid (403) unauthenticated "
            "access, got %d instead" % response.status_code,
        )

    def testClassSubjectsFields(self):
        """Each entry in class_subjects['classes'] has all required fields."""
        required_fields = ('id', 'status', 'title', 'category', 'category_id',
                           'grade_min', 'grade_max', 'emailcode', 'sections', 'teachers')
        for cls_data in self.classes_data['classes']:
            for field in required_fields:
                self.assertIn(field, cls_data,
                              "class entry missing field '%s'" % field)

    def testClassSubjectsSectionsAreLists(self):
        """The 'sections' field in each class_subjects entry is a list of unique ints."""
        for cls_data in self.classes_data['classes']:
            cid = cls_data.get('id')
            sections = cls_data['sections']
            self.assertIsInstance(sections, list,
                                  "sections should be a list for class id=%s" % cid)
            for sec_id in sections:
                self.assertIsInstance(sec_id, int,
                                      "section id should be an int, got %r" % sec_id)
            # No duplicate section IDs within a class.
            self.assertEqual(len(sections), len(set(sections)),
                             "Duplicate section IDs for class id=%s: %r" % (cid, sections))

    def testClassSubjectsTeachersAreListed(self):
        """The 'teachers' field in each class_subjects entry is a list of ints."""
        for cls_data in self.classes_data['classes']:
            cid = cls_data.get('id')
            teachers = cls_data['teachers']
            self.assertIsInstance(teachers, list,
                                  "teachers should be a list for class id=%s" % cid)
            for t_id in teachers:
                self.assertIsInstance(t_id, int,
                                      "teacher id should be an int, got %r (class id=%s)"
                                      % (t_id, cid))

    def testClassSubjectsTeachersBlock(self):
        """The top-level 'teachers' block in class_subjects has correct fields."""
        self.assertIn('teachers', self.classes_data,
                      "class_subjects response missing top-level 'teachers' key")
        for t in self.classes_data['teachers']:
            for field in ('id', 'username', 'first_name', 'last_name', 'sections'):
                self.assertIn(field, t,
                              "teachers entry missing field '%s'" % field)
            self.assertIsInstance(t['sections'], list,
                                  "teacher 'sections' should be a list")

    def testClassSubjectsCatalogMode(self):
        """Catalog mode includes extra fields: class_info, prereqs, difficulty."""
        url = '/json/%s/class_subjects/catalog' % self.program.getUrlBase()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_classes = response.json()
        for cls_data in json_classes['classes']:
            for field in ('class_info', 'prereqs', 'difficulty'):
                self.assertIn(field, cls_data,
                              "catalog mode class entry missing field '%s'" % field)

    def testClassSubjectsGradeRange(self):
        """grade_min and grade_max in class_subjects are within the program range
        and grade_min <= grade_max for each class."""
        prog_min = self.program.grade_min
        prog_max = self.program.grade_max
        for cls_data in self.classes_data['classes']:
            cid = cls_data.get('id')
            self.assertLessEqual(cls_data['grade_min'], cls_data['grade_max'],
                                 "grade_min > grade_max for class id=%s" % cid)
            self.assertGreaterEqual(cls_data['grade_min'], prog_min,
                                    "grade_min below program minimum for class id=%s" % cid)
            self.assertLessEqual(cls_data['grade_max'], prog_max,
                                 "grade_max above program maximum for class id=%s" % cid)

