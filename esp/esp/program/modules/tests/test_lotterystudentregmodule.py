__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

from esp.program.models import StudentRegistration
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest


class LotteryStudentRegModuleTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'timeslot_length': 50,
            'timeslot_gap': 10,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
            'num_students': 3,
        })
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()

        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        pm = ProgramModule.objects.get(handler='LotteryStudentRegModule', module_type='learn')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.module.user = self.students[0]

        self.student = self.students[0]
        self.section = self.program.sections()[0]

    def tearDown(self):
        StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
        ).delete()
        super().tearDown()

    def test_isCompleted_false_before_registration(self):
        self.assertFalse(self.module.isCompleted(self.student))

    def test_isCompleted_true_after_registration(self):
        self.section.preregister_student(self.student)
        self.assertTrue(self.module.isCompleted(self.student))

    def test_isCompleted_false_after_unregistration(self):
        self.section.preregister_student(self.student)
        self.assertTrue(self.module.isCompleted(self.student))
        self.section.unpreregister_student(self.student)
        self.assertFalse(self.module.isCompleted(self.student))

    def test_students_returns_registered_student(self):
        self.section.preregister_student(self.student)
        students_map = self.module.students()
        self.assertIn(self.student, students_map['lotteried_students'])

    def test_students_excludes_unregistered_student(self):
        students_map = self.module.students()
        self.assertNotIn(self.student, students_map['lotteried_students'])

    def test_studentDesc_contains_key(self):
        desc = self.module.studentDesc()
        self.assertIn('lotteried_students', desc)

    def test_students_qobject_returns_dict_with_key(self):
        q_map = self.module.students(QObject=True)
        self.assertIn('lotteried_students', q_map)

    def test_lotterystudentreg_get_renders_for_eligible_student(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            "Couldn't log in as student %s" % self.student.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)

    def test_lotterystudentreg_get_blocked_for_anonymous_user(self):
        self.client.logout()
        response = self.client.get(self.module.get_full_path())
        self.assertNotEqual(response.status_code, 200)

    def test_lotterystudentreg_get_blocked_for_teacher(self):
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'lottery', response.content.lower()[:500])

    def test_timeslots_json_returns_200(self):
        response = self.client.get(
            '/learn/%s/timeslots_json' % self.program.getUrlBase()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_timeslots_json_contains_timeslot_ids(self):
        response = self.client.get(
            '/learn/%s/timeslots_json' % self.program.getUrlBase()
        )
        import json
        data = json.loads(response.content)
        program_timeslot_ids = set(
            self.program.getTimeSlotList()[i].id
            for i in range(len(self.program.getTimeSlotList()))
        )
        returned_ids = set(item[0] for item in data)
        self.assertEqual(program_timeslot_ids, returned_ids)

    def test_viewlotteryprefs_get_renders_for_student(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        response = self.client.get(
            '/learn/%s/viewlotteryprefs' % self.program.getUrlBase()
        )
        self.assertEqual(response.status_code, 200)

    def test_viewlotteryprefs_shows_empty_state_before_registration(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        response = self.client.get(
            '/learn/%s/viewlotteryprefs' % self.program.getUrlBase()
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['pempty'])
        self.assertTrue(response.context['iempty'])

    def test_viewlotteryprefs_blocked_for_anonymous_user(self):
        self.client.logout()
        response = self.client.get(
            '/learn/%s/viewlotteryprefs' % self.program.getUrlBase()
        )
        self.assertNotEqual(response.status_code, 200)
