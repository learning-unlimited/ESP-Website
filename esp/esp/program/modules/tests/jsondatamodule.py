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

    def setUp(self):
        super().setUp()
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
        # Ensure endpoints returned successfully before attempting to parse JSON.
        self.assertEqual(
            self.stats_response.status_code, 200,
            f"Expected 200 from /json/{self.program.getUrlBase()}/stats, got {self.stats_response.status_code}. Body snippet: {self.stats_response.content[:200]!r}"
        )
        self.assertEqual(
            self.classes_response.status_code, 200,
            f"Expected 200 from /json/{self.program.getUrlBase()}/class_subjects, got {self.classes_response.status_code}. Body snippet: {self.classes_response.content[:200]!r}"
        )
        # Cache parsed payloads so individual tests don't re-parse repeatedly.
        try:
            self.stats_data = self.stats_response.json()
        except ValueError:
            self.fail(
                f"Failed to parse JSON from /json/{self.program.getUrlBase()}/stats (status {self.stats_response.status_code}). "
                f"Body snippet: {self.stats_response.content[:200]!r}"
            )
        try:
            self.classes_data = self.classes_response.json()
        except ValueError:
            self.fail(
                f"Failed to parse JSON from /json/{self.program.getUrlBase()}/class_subjects (status {self.classes_response.status_code}). "
                f"Body snippet: {self.classes_response.content[:200]!r}"
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
            json_str = f'["{query_label}", {value}]'
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
            json_str = f'["{query_label}", {value}]'
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
        self.assertEqual(len(json_classes["classes"]), classes.count())

        json_classes_dict = dict()
        for json_cls in json_classes["classes"]:
            json_classes_dict[json_cls['id']] = json_cls
        for cls in classes:
            # Very basic check that we're getting the data correctly
            self.assertTrue(cls.id in json_classes_dict)
            self.assertEqual(json_classes_dict[cls.id]['emailcode'], cls.emailcode())

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
                         f"vitals classnum total mismatch: got {total_count}, expected {expected}")

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
                             f"Duplicate section IDs for class id={cid}: {sections!r}")

    def testClassSubjectsTeachersAreListed(self):
        """The 'teachers' field in each class_subjects entry is a list of ints."""
        for cls_data in self.classes_data['classes']:
            cid = cls_data.get('id')
            teachers = cls_data['teachers']
            self.assertIsInstance(teachers, list,
                                  "teachers should be a list for class id=%s" % cid)
            for t_id in teachers:
                self.assertIsInstance(t_id, int,
                                      f"teacher id should be an int, got {t_id!r} (class id={cid})")

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


class JSONModuleManagementTest(ProgramFrameworkTest):
    """Tests for the JSON API endpoints for module management (#4689)."""

    def setUp(self):
        from esp.users.models import ESPUser
        modules = []
        modules.append(ProgramModule.objects.get(handler='AdminCore'))
        modules.append(ProgramModule.objects.get(handler='JSONDataModule'))
        modules += list(ProgramModule.objects.filter(handler='RegProfileModule'))
        modules.append(ProgramModule.objects.get(handler='AvailabilityModule'))
        modules.append(ProgramModule.objects.get(handler='StudentRegConfirm'))

        super(JSONModuleManagementTest, self).setUp(modules=modules)

        # Force creation of ProgramModuleObj rows for all modules.
        self.program.getModules()

        self.adminUser, created = ESPUser.objects.get_or_create(username='admin_json_mgmt')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

    # -----------------------------------------------------------------------
    # URL helpers
    # -----------------------------------------------------------------------

    def _url(self, endpoint):
        return '/json/%s/%s' % (self.program.url, endpoint)

    # -----------------------------------------------------------------------
    # modules_list
    # -----------------------------------------------------------------------

    def test_modules_list_requires_admin(self):
        """modules_list returns 302 (or 403) when not logged in."""
        r = self.client.get(self._url('modules_list'))
        self.assertIn(r.status_code, [302, 403])

    def test_modules_list_returns_200_for_admin(self):
        """modules_list returns 200 for an admin user."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_list'))
        self.assertEqual(r.status_code, 200)

    def test_modules_list_returns_json(self):
        """modules_list response body is valid JSON with a 'modules' key."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_list'))
        data = json.loads(r.content)
        self.assertIn('modules', data)
        self.assertIsInstance(data['modules'], list)

    def test_modules_list_entries_have_expected_keys(self):
        """Each entry in modules_list has all required keys."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_list'))
        data = json.loads(r.content)
        required_keys = {'id', 'module_type', 'handler', 'admin_title',
                         'link_title', 'seq', 'required'}
        for entry in data['modules']:
            for key in required_keys:
                self.assertIn(key, entry,
                              'Missing key %r in entry %r' % (key, entry))

    def test_modules_list_only_step_modules(self):
        """modules_list only returns modules where inModulesList() is True."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_list'))
        data = json.loads(r.content)
        step_ids = set()
        for tl in ('learn', 'teach'):
            step_ids.update(
                m.id for m in self.program.getModules(tl=tl) if m.inModulesList()
            )
        returned_ids = {entry['id'] for entry in data['modules']}
        self.assertEqual(returned_ids, step_ids)

    def test_modules_list_constraints_present_for_locked_modules(self):
        """modules_list includes a 'constraints' dict for constrained modules."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_list'))
        data = json.loads(r.content)
        reg_profile_entries = [
            e for e in data['modules'] if e['handler'] == 'RegProfileModule'
        ]
        for entry in reg_profile_entries:
            self.assertIn('constraints', entry)
            self.assertTrue(entry['constraints']['required_locked'])
            self.assertTrue(entry['constraints']['position_locked'])

    # -----------------------------------------------------------------------
    # module_update
    # -----------------------------------------------------------------------

    def test_module_update_requires_post(self):
        """module_update rejects GET requests with 405."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('module_update'))
        self.assertEqual(r.status_code, 405)

    def test_module_update_requires_admin(self):
        """module_update returns 302 (or 403) when not logged in."""
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'seq': 20}),
            content_type='application/json',
        )
        self.assertIn(r.status_code, [302, 403])

    def test_module_update_seq(self):
        """module_update can update seq for a module."""
        self.client.login(username='admin_json_mgmt', password='password')
        # Pick a module that is not position-locked so the update sticks.
        pmo = ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler='AvailabilityModule',
        ).first()
        if pmo is None:
            pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        new_seq = pmo.seq + 100
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'seq': new_seq}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmo.refresh_from_db()
        self.assertEqual(pmo.seq, new_seq)

    def test_module_update_required_label(self):
        """module_update can set required_label."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'required_label': 'Sign up now'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmo.refresh_from_db()
        self.assertEqual(pmo.required_label, 'Sign up now')

    def test_module_update_link_title(self):
        """module_update can set link_title."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'link_title': 'My Title'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmo.refresh_from_db()
        self.assertEqual(pmo.link_title, 'My Title')

    def test_module_update_invalid_id(self):
        """module_update returns 404 for an ID not in this program."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': 999999, 'seq': 5}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_module_update_rejects_bool_as_seq(self):
        """module_update rejects a JSON boolean for seq (bool is a subclass of int)."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'seq': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)
        data = json.loads(r.content)
        self.assertIn('error', data)

    def test_module_update_rejects_non_integer_seq(self):
        """module_update returns 400 when seq is a string."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'seq': 'ten'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_overlong_required_label(self):
        """module_update returns 400 when required_label exceeds 80 characters."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'required_label': 'x' * 81}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_overlong_link_title(self):
        """module_update returns 400 when link_title exceeds 64 characters."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'link_title': 'y' * 65}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_enforces_constraints(self):
        """module_update re-enforces constraints after saving (e.g. RegProfileModule stays seq=0)."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(
            program=self.program, module__handler='RegProfileModule'
        ).first()
        if pmo is None:
            return  # module not in this program; skip
        self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'seq': 500}),
            content_type='application/json',
        )
        pmo.refresh_from_db()
        self.assertEqual(pmo.seq, 0)

    def test_module_update_rejects_invalid_json(self):
        """module_update returns 400 for a malformed JSON body."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('module_update'),
            data='not json{{',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_non_integer_id(self):
        """module_update returns 400 when id is not an integer."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': 'abc', 'seq': 5}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', json.loads(r.content))

    def test_module_update_rejects_no_valid_fields(self):
        """module_update returns 400 when no recognised fields are provided."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'color': 'blue'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_non_boolean_required(self):
        """module_update returns 400 when required is not a boolean."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'required': 'yes'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_non_string_required_label(self):
        """module_update returns 400 when required_label is not a string."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'required_label': 5}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_module_update_rejects_non_string_link_title(self):
        """module_update returns 400 when link_title is not a string."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        r = self.client.post(
            self._url('module_update'),
            data=json.dumps({'id': pmo.id, 'link_title': 5}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    # -----------------------------------------------------------------------
    # modules_reorder
    # -----------------------------------------------------------------------

    def test_modules_reorder_requires_post(self):
        """modules_reorder rejects GET requests with 405."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_reorder'))
        self.assertEqual(r.status_code, 405)

    def test_modules_reorder_requires_admin(self):
        """modules_reorder returns 302 (or 403) when not logged in."""
        pmos = list(ProgramModuleObj.objects.filter(program=self.program)[:2])
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': [p.id for p in pmos]}),
            content_type='application/json',
        )
        self.assertIn(r.status_code, [302, 403])

    def test_modules_reorder_updates_seq(self):
        """modules_reorder sets increasing seq values in submission order."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmos = list(ProgramModuleObj.objects.filter(program=self.program)
                    .order_by('seq')[:3])
        # Submit in reverse to force a real change.
        ordered_ids = [p.id for p in reversed(pmos)]
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': ordered_ids}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['updated'], len(ordered_ids))

        # seq values must be monotonically increasing in the submitted order
        # (constraint enforcement may override some, but relative ordering holds
        # for unconstrained modules).
        db_pmos = {p.id: p for p in ProgramModuleObj.objects.filter(id__in=ordered_ids)}
        seqs = [db_pmos[mid].seq for mid in ordered_ids]
        self.assertEqual(seqs, sorted(seqs), 'seq values should be increasing')

    def test_modules_reorder_starting_seq(self):
        """modules_reorder starts seq at 12 (room for non-step modules earlier)."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmos = list(ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler='AvailabilityModule',
        ))
        if not pmos:
            return
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': [pmos[0].id]}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmos[0].refresh_from_db()
        # AvailabilityModule is required_locked but not position_locked, so seq >= 12.
        self.assertGreaterEqual(pmos[0].seq, 12)

    def test_modules_reorder_missing_ids(self):
        """modules_reorder returns 404 when IDs are not in the program."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': [999999]}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_modules_reorder_requires_list_of_integers(self):
        """modules_reorder returns 400 when module_ids contains non-integers."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': ['a', 'b']}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_modules_reorder_rejects_non_list_module_ids(self):
        """modules_reorder returns 400 when module_ids is not a list."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': 'not-a-list'}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_modules_reorder_rejects_invalid_json(self):
        """modules_reorder returns 400 for a malformed JSON body."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reorder'),
            data='not json{{',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_modules_reorder_enforces_constraints(self):
        """modules_reorder enforces constraints: RegProfileModule stays seq=0."""
        self.client.login(username='admin_json_mgmt', password='password')
        reg_pmos = list(ProgramModuleObj.objects.filter(
            program=self.program, module__handler='RegProfileModule'
        ))
        if not reg_pmos:
            return
        other_pmos = list(ProgramModuleObj.objects.filter(
            program=self.program
        ).exclude(module__handler='RegProfileModule')[:2])
        # Put RegProfileModule last — constraint enforcement must fix it.
        to_reorder = other_pmos + reg_pmos
        r = self.client.post(
            self._url('modules_reorder'),
            data=json.dumps({'module_ids': [p.id for p in to_reorder]}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        for pmo in reg_pmos:
            pmo.refresh_from_db()
            self.assertEqual(pmo.seq, 0)

    # -----------------------------------------------------------------------
    # modules_reset
    # -----------------------------------------------------------------------

    def test_modules_reset_requires_post(self):
        """modules_reset rejects GET requests with 405."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.get(self._url('modules_reset'))
        self.assertEqual(r.status_code, 405)

    def test_modules_reset_requires_admin(self):
        """modules_reset returns 302 (or 403) when not logged in."""
        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'seq': True}),
            content_type='application/json',
        )
        self.assertIn(r.status_code, [302, 403])

    def test_modules_reset_seq(self):
        """modules_reset restores seq to module defaults for all step modules."""
        self.client.login(username='admin_json_mgmt', password='password')
        # Dirty seq for all modules.
        pmos = list(ProgramModuleObj.objects.filter(program=self.program))
        for pmo in pmos:
            pmo.seq = 999
        ProgramModuleObj.objects.bulk_update(pmos, ['seq'])

        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'seq': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data['status'], 'ok')

        # Step modules should have seq == module default (or constraint override).
        for tl in ('learn', 'teach'):
            for pmo in self.program.getModules(tl=tl):
                if not pmo.inModulesList():
                    continue
                pmo_db = ProgramModuleObj.objects.get(id=pmo.id)
                self.assertEqual(pmo_db.seq, pmo.module.seq)

    def test_modules_reset_required_label(self):
        """modules_reset clears required_label overrides."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        pmo.required_label = 'before reset'
        pmo.save()

        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'required_label': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmo.refresh_from_db()
        self.assertEqual(pmo.required_label, '')

    def test_modules_reset_link_title(self):
        """modules_reset clears link_title overrides."""
        self.client.login(username='admin_json_mgmt', password='password')
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        pmo.link_title = 'before reset'
        pmo.save()

        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'link_title': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        pmo.refresh_from_db()
        self.assertEqual(pmo.link_title, '')

    def test_modules_reset_rejects_invalid_json(self):
        """modules_reset returns 400 for a malformed JSON body."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reset'),
            data='not json{{',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_modules_reset_requires_at_least_one_field(self):
        """modules_reset returns 400 when no fields are specified."""
        self.client.login(username='admin_json_mgmt', password='password')
        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_modules_reset_enforces_constraints(self):
        """modules_reset enforces hard-coded constraints after resetting seq."""
        self.client.login(username='admin_json_mgmt', password='password')
        reg_pmos = list(ProgramModuleObj.objects.filter(
            program=self.program, module__handler='RegProfileModule'
        ))
        if not reg_pmos:
            return
        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'seq': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        for pmo in reg_pmos:
            pmo.refresh_from_db()
            # Constraint override: RegProfileModule is always seq=0.
            self.assertEqual(pmo.seq, 0)

    def test_modules_reset_confirm_stays_not_required(self):
        """modules_reset + constraint enforcement leaves StudentRegConfirm not required."""
        self.client.login(username='admin_json_mgmt', password='password')
        confirm_pmos = list(ProgramModuleObj.objects.filter(
            program=self.program, module__handler='StudentRegConfirm'
        ))
        if not confirm_pmos:
            return
        r = self.client.post(
            self._url('modules_reset'),
            data=json.dumps({'required': True}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        for pmo in confirm_pmos:
            pmo.refresh_from_db()
            self.assertFalse(pmo.required)

