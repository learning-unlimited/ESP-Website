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

from decimal import Decimal
from esp.accounting.controllers import ProgramAccountingController
from esp.accounting.models import LineItemType
from esp.program.models import ClassSubject, ClassCategories, PhaseZeroRecord
from esp.program.modules.handlers.studentextracosts import CostItem, MultiCostItem
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import Record, RecordType, Permission


class StudentExtraCostsTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1,
                      base_cost=50, sibling_discount=10)
        self.add_student_profiles()
        self.student = self.students[0]
        pac = ProgramAccountingController(self.program)
        pac.setup_accounts()
        self.tshirt_item = LineItemType.objects.create(
            text='T-Shirt', program=self.program, amount_dec=Decimal('15.00'),
            required=False, max_quantity=1, for_finaid=False)
        self.meal_item = LineItemType.objects.create(
            text='Meal Plan', program=self.program, amount_dec=Decimal('25.00'),
            required=False, max_quantity=3, for_finaid=True)

    def test_extracosts_page_loads(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/extracosts' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_students_query(self):
        module = self.program.getModule('StudentExtraCosts')
        for qobj in [True, False]:
            result = module.students(QObject=qobj)
            self.assertIsInstance(result, dict)

    def test_is_completed(self):
        module = self.program.getModule('StudentExtraCosts')
        module.user = self.student
        self.assertFalse(module.isCompleted())
        rt, _ = RecordType.objects.get_or_create(name='extra_costs_done')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_lineitemtypes_excludes_admission(self):
        module = self.program.getModule('StudentExtraCosts')
        admission_items = list(LineItemType.objects.filter(program=self.program, text__icontains='admission'))
        self.assertTrue(
            admission_items,
            'Expected setup_accounts() to create at least one admission line item for this program'
        )
        module_items = list(module.lineitemtypes())
        for item in admission_items:
            self.assertNotIn(item, module_items)
            self.assertIn('admission', item.text.lower())

    def test_is_required(self):
        module = self.program.getModule('StudentExtraCosts')
        self.tshirt_item.required = False
        self.tshirt_item.save()
        self.meal_item.required = False
        self.meal_item.save()
        self.assertFalse(module.isRequired())
        self.tshirt_item.required = True
        self.tshirt_item.save()
        self.assertTrue(module.isRequired())

    def test_cost_item_form(self):
        form = CostItem(data={'cost': True}, cost=15, required=False, for_finaid=False)
        self.assertTrue(form.is_valid())
        form = CostItem(data={}, cost=15, required=True, for_finaid=False)
        self.assertFalse(form.is_valid())

    def test_multi_cost_item_form(self):
        form = MultiCostItem(data={'count': 2}, cost=25, required=False, max_quantity=5, for_finaid=True)
        self.assertTrue(form.is_valid())
        form = MultiCostItem(data={'count': 10}, cost=25, required=False, max_quantity=5, for_finaid=True)
        self.assertFalse(form.is_valid())

    def test_extracosts_post(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.post('/learn/%s/extracosts' % self.program.getUrlBase(),
                                    {'%s-cost' % self.tshirt_item.id: 'on'}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_student_desc(self):
        module = self.program.getModule('StudentExtraCosts')
        desc = module.studentDesc()
        self.assertIsInstance(desc, dict)

    def test_is_step(self):
        module = self.program.getModule('StudentExtraCosts')
        self.assertTrue(module.isStep())


class StudentRegCoreTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=5, num_teachers=3, classes_per_teacher=2, base_cost=100)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_student_reg_page_loads(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/studentreg' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_students_query(self):
        module = self.program.getModule('StudentRegCore')
        students = module.students(QObject=False)
        self.assertIn('confirmed', students)
        self.assertIn('attended', students)
        self.assertIn('checked_in', students)
        self.assertIn('checked_out', students)

    def test_have_paid(self):
        module = self.program.getModule('StudentRegCore')
        self.assertFalse(module.have_paid(self.student))

    def test_student_desc(self):
        module = self.program.getModule('StudentRegCore')
        desc = module.studentDesc()
        self.assertIn('confirmed', desc)
        self.assertIn(self.program.niceName(), desc['attended'])

    def test_confirmreg_page(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_cancelreg(self):
        rt, _ = RecordType.objects.get_or_create(name='reg_confirmed')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/cancelreg' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_confirmed_students(self):
        module = self.program.getModule('StudentRegCore')
        self.assertEqual(module.students(QObject=False)['confirmed'].count(), 0)
        rt, _ = RecordType.objects.get_or_create(name='reg_confirmed')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertIn(self.student, module.students(QObject=False)['confirmed'])

    def test_waitlist_students(self):
        self.program.program_allow_waitlist = True
        self.program.save()
        module = self.program.getModule('StudentRegCore')
        self.assertIn('waitlisted_students', module.students(QObject=False))

    def test_students_qobject_mode(self):
        module = self.program.getModule('StudentRegCore')
        students = module.students(QObject=True)
        self.assertIn('confirmed', students)
        self.assertIn('attended', students)

    def test_is_step(self):
        module = self.program.getModule('StudentRegCore')
        self.assertFalse(module.isStep())


class StudentRegPhaseZeroTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=5, num_teachers=3, classes_per_teacher=2)
        self.add_student_profiles()
        self.student = self.students[0]
        Tag.setTag('student_lottery_group_max', target=self.program, value='4')

    def test_students_query(self):
        module = self.program.getModule('StudentRegPhaseZero')
        for qobj in [True, False]:
            result = module.students(QObject=qobj)
            self.assertIn('phasezero', result)

    def test_phase_zero_page_loads(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/studentregphasezero' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_phase_zero_record(self):
        module = self.program.getModule('StudentRegPhaseZero')
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        self.assertTrue(PhaseZeroRecord.objects.filter(user=self.student, program=self.program).exists())
        self.assertIn(self.student, module.students(QObject=False)['phasezero'])

    def test_studentlookup(self):
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        logged_in = self.client.login(username=self.students[1].username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/studentlookup?username=%s' % (
            self.program.getUrlBase(), self.student.username[:3]), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_joingroup_errors(self):
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)
        logged_in = self.client.login(username=self.students[1].username, password='password')
        self.assertTrue(logged_in)
        response = self.client.post('/learn/%s/joingroup' % self.program.getUrlBase(), {}, follow=True)
        self.assertEqual(response.status_code, 200)
        Permission.objects.create(user=self.students[1], permission_type='Student/PhaseZero', program=self.program)
        response = self.client.post('/learn/%s/joingroup' % self.program.getUrlBase(), {'student_selected': '999999'}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_student_desc(self):
        module = self.program.getModule('StudentRegPhaseZero')
        desc = module.studentDesc()
        self.assertIn('phasezero', desc)

    def test_is_step(self):
        module = self.program.getModule('StudentRegPhaseZero')
        self.assertFalse(module.isStep())

    def test_in_modules_list(self):
        module = self.program.getModule('StudentRegPhaseZero')
        self.assertTrue(module.inModulesList())


class StudentRegConfirmTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_confirmreg_page(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_do_confirmreg_redirects(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/do_confirmreg' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 302)
        self.assertIn('confirmreg', response.url)

    def test_is_completed(self):
        module = self.program.getModule('StudentRegConfirm')
        module.user = self.student
        self.assertFalse(module.isCompleted())
        rt, _ = RecordType.objects.get_or_create(name='reg_confirmed')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_hide_not_required(self):
        module = self.program.getModule('StudentRegConfirm')
        self.assertTrue(module.hideNotRequired())

    def test_confirmreg_with_registration(self):
        sections = list(self.program.sections())
        self.assertTrue(sections, 'Expected test setup to create at least one section')
        sections[0].preregister_student(self.student)
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)


class LotteryStudentRegTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=5, num_teachers=3, classes_per_teacher=2)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_students_query(self):
        module = self.program.getModule('LotteryStudentRegModule')
        students = module.students(QObject=False)
        self.assertIn('lotteried_students', students)

    def test_is_completed(self):
        module = self.program.getModule('LotteryStudentRegModule')
        module.user = self.student
        self.assertFalse(module.isCompleted())
        sections = list(self.program.sections())
        self.assertTrue(sections, 'Expected test setup to create at least one section')
        sections[0].preregister_student(self.student)
        self.assertTrue(module.isCompleted())


class StudentAcknowledgementTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3)
        self.add_student_profiles()
        self.student = self.students[0]
        RecordType.objects.get_or_create(name='studentacknowledgement')

    def test_is_completed(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        module.user = self.student
        self.assertFalse(module.isCompleted())
        rt = RecordType.objects.get(name='studentacknowledgement')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())

    def test_students_query(self):
        module = self.program.getModule('StudentAcknowledgementModule')
        self.assertEqual(module.students(QObject=False)['studentacknowledgement'].count(), 0)
        rt = RecordType.objects.get(name='studentacknowledgement')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertIn(self.student, module.students(QObject=False)['studentacknowledgement'])


class StudentLunchSelectionTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.student = self.students[0]
        self.lunch_category, _ = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        self.lunch_class, _ = ClassSubject.objects.get_or_create(
            title='Lunch Period', category=self.lunch_category, grade_min=7, grade_max=12,
            parent_program=self.program, class_size_max=100, class_info='Lunch break')
        self.lunch_class.accept()
        section = self.lunch_class.add_section(duration=50 / 60.0)
        if self.program.getTimeSlots():
            section.meeting_times.add(self.program.getTimeSlots()[0])
        RecordType.objects.get_or_create(name='lunch_selected')

    def test_is_completed(self):
        module = self.program.getModule('StudentLunchSelection')
        module.user = self.student
        self.assertFalse(module.isCompleted())
        rt = RecordType.objects.get(name='lunch_selected')
        Record.objects.create(user=self.student, program=self.program, event=rt)
        self.assertTrue(module.isCompleted())


class StudentSurveyModuleTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3)
        self.add_student_profiles()
        self.student = self.students[0]

    def test_students_query(self):
        module = self.program.getModule('StudentSurveyModule')
        for qobj in [True, False]:
            result = module.students(QObject=qobj)
            self.assertIn('student_survey', result)

    def test_student_desc(self):
        module = self.program.getModule('StudentSurveyModule')
        desc = module.studentDesc()
        self.assertIn('student_survey', desc)

    def test_is_step_default(self):
        module = self.program.getModule('StudentSurveyModule')
        self.assertFalse(module.isStep())


class StudentCertModuleTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_is_step_before_program_ends(self):
        module = self.program.getModule('StudentCertModule')
        module.user = self.student
        self.assertFalse(module.isStep())


class StudentOnsiteTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=3, num_teachers=2, classes_per_teacher=1)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_studentonsite_page(self):
        logged_in = self.client.login(username=self.student.username, password='password')
        self.assertTrue(logged_in)
        response = self.client.get('/learn/%s/studentonsite' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)


class StudentClassRegModuleTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(num_students=5, num_teachers=3, classes_per_teacher=2)
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_catalog_json(self):
        response = self.client.get('/learn/%s/catalog_json' % self.program.getUrlBase(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_class_info_page(self):
        sections = list(self.program.sections())
        self.assertTrue(sections, 'Expected test setup to create at least one section')
        response = self.client.get('/learn/%s/classinfo/%s' % (
            self.program.getUrlBase(), sections[0].parent_class.id), follow=True)
        self.assertIn(response.status_code, [200, 404])

    def test_students_query(self):
        module = self.program.getModule('StudentClassRegModule')
        students = module.students(QObject=False)
        self.assertIn('enrolled', students)
        self.assertIn('enrolled_non_lunch', students)
        self.assertIn('classreg', students)

    def test_student_desc(self):
        module = self.program.getModule('StudentClassRegModule')
        desc = module.studentDesc()
        self.assertIn('enrolled', desc)
        self.assertIn('enrolled_non_lunch', desc)

    def test_enrolled_non_lunch_excludes_lunch_only_students(self):
        module = self.program.getModule('StudentClassRegModule')

        lunch_category, _ = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        lunch_class = ClassSubject.objects.create(
            title='Lunch Period',
            category=lunch_category,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
            class_size_max=100,
            class_info='Lunch break',
        )
        lunch_class.makeTeacher(self.teachers[0])
        lunch_class.accept()
        lunch_section = lunch_class.add_section(duration=50 / 60.0)
        if self.program.getTimeSlots():
            lunch_section.meeting_times.add(self.program.getTimeSlots()[0])

        regular_section = self.program.sections().exclude(parent_class__category__category='Lunch').first()
        self.assertIsNotNone(regular_section, 'Expected at least one non-lunch section in the test program')

        lunch_only_student = self.students[0]
        regular_student = self.students[1]

        lunch_section.preregister_student(lunch_only_student, fast_force_create=True)
        regular_section.preregister_student(regular_student, fast_force_create=True)

        students = module.students(QObject=False)
        self.assertIn('enrolled_non_lunch', students)
        self.assertNotIn(lunch_only_student, students['enrolled_non_lunch'])
        self.assertIn(regular_student, students['enrolled_non_lunch'])
