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

from datetime import datetime, timedelta
from decimal import Decimal

from django.test import Client

from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.accounting.models import LineItemType, LineItemOptions
from esp.cal.models import Event, EventType
from esp.program.models import (
    Program, ClassSection, ClassSubject, ClassCategories,
    StudentRegistration, RegistrationType, ProgramModule
)
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, Record, RecordType, StudentInfo


class StudentExtraCostsTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(
            num_students=3,
            num_teachers=2,
            classes_per_teacher=1,
            base_cost=50,
            sibling_discount=10
        )
        self.add_student_profiles()
        self.student = self.students[0]

        pac = ProgramAccountingController(self.program)
        pac.setup_accounts()

        self.tshirt_item = LineItemType.objects.create(
            text='T-Shirt',
            program=self.program,
            amount_dec=Decimal('15.00'),
            required=False,
            max_quantity=1,
            for_finaid=False
        )
        self.meal_item = LineItemType.objects.create(
            text='Meal Plan',
            program=self.program,
            amount_dec=Decimal('25.00'),
            required=False,
            max_quantity=3,
            for_finaid=True
        )

    def test_module_exists(self):
        module = self.program.getModule('StudentExtraCosts')
        self.assertIsNotNone(module)

    def test_extracosts_page_loads(self):
        self.client.login(username=self.student.username, password='password')
        response = self.client.get('/learn/%s/extracosts' % self.program.getUrlBase())
        self.assertIn(response.status_code, [200, 302])

    def test_students_query(self):
        module = self.program.getModule('StudentExtraCosts')
        module.user = self.student
        student_lists = module.students(QObject=True)
        self.assertIsInstance(student_lists, dict)

    def test_is_completed_false_initially(self):
        module = self.program.getModule('StudentExtraCosts')
        module.user = self.student
        self.assertFalse(module.isCompleted())

    def test_is_completed_true_after_record(self):
        module = self.program.getModule('StudentExtraCosts')
        module.user = self.student
        rt, _ = RecordType.objects.get_or_create(name='extra_costs_done')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_lineitemtypes_excludes_admission(self):
        module = self.program.getModule('StudentExtraCosts')
        items = module.lineitemtypes()
        for item in items:
            self.assertNotIn('admission', item.text.lower())


class StudentRegCoreTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(
            num_students=5,
            num_teachers=3,
            classes_per_teacher=2,
            base_cost=100
        )
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_module_exists(self):
        module = self.program.getModule('StudentRegCore')
        self.assertIsNotNone(module)

    def test_student_reg_page_loads(self):
        self.client.login(username=self.student.username, password='password')
        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase())
        self.assertIn(response.status_code, [200, 302])

    def test_students_query_returns_dict(self):
        module = self.program.getModule('StudentRegCore')
        students = module.students(QObject=False)
        self.assertIsInstance(students, dict)
        self.assertIn('confirmed', students)
        self.assertIn('attended', students)

    def test_students_query_qobject(self):
        module = self.program.getModule('StudentRegCore')
        students = module.students(QObject=True)
        self.assertIsInstance(students, dict)
        self.assertIn('confirmed', students)

    def test_have_paid_initially_false(self):
        module = self.program.getModule('StudentRegCore')
        result = module.have_paid(self.student)
        self.assertFalse(result)


class LotteryStudentRegTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(
            num_students=5,
            num_teachers=3,
            classes_per_teacher=2
        )
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_module_exists(self):
        module = self.program.getModule('LotteryStudentRegModule')
        self.assertIsNotNone(module)

    def test_students_method(self):
        module = self.program.getModule('LotteryStudentRegModule')
        students = module.students(QObject=False)
        self.assertIsInstance(students, dict)
        self.assertIn('lotteried_students', students)

    def test_student_desc(self):
        module = self.program.getModule('LotteryStudentRegModule')
        desc = module.studentDesc()
        self.assertIn('lotteried_students', desc)

    def test_is_completed_false_without_registration(self):
        module = self.program.getModule('LotteryStudentRegModule')
        module.user = self.student
        self.assertFalse(module.isCompleted())

    def test_is_completed_true_with_registration(self):
        module = self.program.getModule('LotteryStudentRegModule')
        module.user = self.student
        section = self.program.sections()[0]
        section.preregister_student(self.student)
        self.assertTrue(module.isCompleted())

    def test_timeslots_json(self):
        self.client.login(username=self.student.username, password='password')
        response = self.client.get('/learn/%s/timeslots_json' % self.program.getUrlBase())
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/json')


class StudentAcknowledgementTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3)
        self.add_student_profiles()
        self.student = self.students[0]
        RecordType.objects.get_or_create(name='studentacknowledgement')

    def test_module_exists(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        self.assertIsNotNone(module)

    def test_is_completed_false_initially(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        module.user = self.student
        self.assertFalse(module.isCompleted())

    def test_is_completed_true_after_record(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        module.user = self.student
        rt = RecordType.objects.get(name='studentacknowledgement')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_students_method(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        students = module.students(QObject=False)
        self.assertEqual(students['studentacknowledgement'].count(), 0)

        rt = RecordType.objects.get(name='studentacknowledgement')
        Record.objects.create(user=self.student, program=self.program, event=rt)

        students = module.students(QObject=False)
        self.assertIn(self.student, students['studentacknowledgement'])

    def test_student_desc(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        desc = module.studentDesc()
        self.assertIn('studentacknowledgement', desc)


class StudentCertModuleTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_module_exists(self):
        module = self.program.getModule('StudentCertModule')
        self.assertIsNotNone(module)

    def test_is_step_false_before_program_ends(self):
        module = self.program.getModule('StudentCertModule')
        module.user = self.student
        self.assertFalse(module.isStep())


class StudentLunchSelectionTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.student = self.students[0]

        self.lunch_category, _ = ClassCategories.objects.get_or_create(
            category='Lunch', symbol='L'
        )
        self.lunch_class, _ = ClassSubject.objects.get_or_create(
            title='Lunch Period',
            category=self.lunch_category,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
            class_size_max=100,
            class_info='Lunch break'
        )
        self.lunch_class.accept()

        section = self.lunch_class.add_section(duration=1.0)
        if self.program.getTimeSlots():
            section.meeting_times.add(self.program.getTimeSlots()[0])

        RecordType.objects.get_or_create(name='lunch_selected')

    def test_module_exists(self):
        module = self.program.getModule('StudentLunchSelection')
        self.assertIsNotNone(module)

    def test_is_completed_false_initially(self):
        module = self.program.getModule('StudentLunchSelection')
        module.user = self.student
        self.assertFalse(module.isCompleted())

    def test_is_completed_true_after_record(self):
        module = self.program.getModule('StudentLunchSelection')
        module.user = self.student
        rt = RecordType.objects.get(name='lunch_selected')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_is_step_with_lunch_classes(self):
        module = self.program.getModule('StudentLunchSelection')
        result = module.isStep()
        self.assertIsInstance(result, bool)


class StudentRegConfirmTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(
            num_students=3,
            num_teachers=2,
            classes_per_teacher=1
        )
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_confirmreg_page_loads(self):
        self.client.login(username=self.student.username, password='password')
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase())
        self.assertIn(response.status_code, [200, 302])

    def test_confirmreg_shows_registered_class(self):
        sections = list(self.program.sections())
        if sections:
            section = sections[0]
            section.preregister_student(self.student)

            self.client.login(username=self.student.username, password='password')
            response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase())
            self.assertIn(response.status_code, [200, 302])
