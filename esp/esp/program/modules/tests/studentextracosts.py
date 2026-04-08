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

from django.test import TestCase

from esp.accounting.controllers import IndividualAccountingController, ProgramAccountingController
from esp.accounting.models import LineItemOptions, LineItemType
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.modules.handlers.studentextracosts import CostItem, MultiCostItem, MultiSelectCostItem
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class StudentExtraCostsFormTests(TestCase):
    """Unit tests for dynamic form helpers used by StudentExtraCosts."""

    def test_cost_item_valid_when_checked(self):
        data = {'1-cost': 'on'}
        f = CostItem(data, prefix='1', required=False, cost=10, for_finaid=True)
        self.assertTrue(f.is_valid())
        self.assertTrue(f.cleaned_data['cost'])

    def test_cost_item_invalid_when_required_and_unchecked(self):
        data = {}
        f = CostItem(data, prefix='1', required=True, cost=10, for_finaid=False)
        self.assertFalse(f.is_valid())

    def test_multi_cost_item_valid_count(self):
        data = {'1-count': '2'}
        f = MultiCostItem(data, prefix='1', required=False, max_quantity=10, cost=5, for_finaid=False)
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['count'], 2)

    def test_multi_cost_item_invalid_above_max(self):
        data = {'1-count': '99'}
        f = MultiCostItem(data, prefix='1', required=False, max_quantity=10, cost=5, for_finaid=False)
        self.assertFalse(f.is_valid())

    def test_multi_select_cost_item_non_custom_valid(self):
        choices = [(1, 'A -- $1.00'), (2, 'B -- $2.00')]
        data = {'m-option': '1'}
        f = MultiSelectCostItem(
            data,
            prefix='m',
            choices=choices,
            required=True,
            is_custom=False,
            option_data={},
        )
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['option'], '1')


class StudentExtraCostsModuleTests(ProgramFrameworkTest):
    """Integration tests for StudentExtraCosts view: accounting + completion record."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'timeslot_length': 50,
            'timeslot_gap': 10,
            'num_teachers': 6,
            'classes_per_teacher': 1,
            'sections_per_class': 2,
            'num_rooms': 6,
            'sibling_discount': 0,
        })
        super().setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()

        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.students[0]

    def _setup_extracosts_accounting(self, program_cost=25.0):
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(
            program_cost,
            [('Item1', 10, 1), ('Item2', 5, 10)],
            [('Food', [('Small', 3), ('Large', 7)])],
        )
        lit_food = LineItemType.objects.get(program=self.program, text='Food')
        LineItemType.objects.filter(id=lit_food.id).update(for_finaid=True)
        # Add a custom-amount option so MultiSelectCostItem uses ChoiceWithOtherField when selected.
        LineItemOptions.objects.create(
            lineitem_type=lit_food,
            description='Pay what you can',
            amount_dec=None,
            is_custom=True,
        )

    def test_extracosts_success_redirect_and_completion_record(self):
        """Valid POST applies preferences, redirects, and creates extra_costs_done Record."""
        program_cost = 25.0
        self._setup_extracosts_accounting(program_cost)

        student = self.students[0]
        iac = IndividualAccountingController(self.program, student)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
            "Couldn't log in as student",
        )

        rt = RecordType.objects.get(name='extra_costs_done')
        Record.objects.filter(user=student, program=self.program, event=rt).delete()

        lit1 = LineItemType.objects.get(program=self.program, text='Item1')
        lit2 = LineItemType.objects.get(program=self.program, text='Item2')

        response = self.client.post(
            '/learn/%s/extracosts' % self.program.getUrlBase(),
            {
                '%d-cost' % lit1.id: 'checked',
                '%d-count' % lit2.id: '0',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/%s/studentreg' % self.program.url, response['Location'])
        self.assertEqual(iac.amount_due(), program_cost + 10)
        self.assertTrue(
            Record.objects.filter(user=student, program=self.program, event=rt).exists(),
            'extra_costs_done Record should exist after successful submit',
        )

    def test_extracosts_custom_option_without_amount_renders_error(self):
        """Custom line-item option selected without an amount: no redirect, error banner, no Record."""
        program_cost = 25.0
        self._setup_extracosts_accounting(program_cost)

        student = self.students[1]
        iac = IndividualAccountingController(self.program, student)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
            "Couldn't log in as student",
        )

        rt = RecordType.objects.get(name='extra_costs_done')
        Record.objects.filter(user=student, program=self.program, event=rt).delete()

        lit2 = LineItemType.objects.get(program=self.program, text='Item2')
        lit_food = LineItemType.objects.get(program=self.program, text='Food')
        custom_opt = lit_food.lineitemoptions_set.filter(is_custom=True).first()
        self.assertIsNotNone(custom_opt)

        due_before = iac.amount_due()

        # ChoiceWithOtherField posts as multi<id>-option_0 (choice) and multi<id>-option_1 (amount).
        response = self.client.post(
            '/learn/%s/extracosts' % self.program.getUrlBase(),
            {
                '%d-count' % lit2.id: '0',
                'multi%d-option_0' % lit_food.id: str(custom_opt.id),
                'multi%d-option_1' % lit_food.id: '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'You selected a choice with a custom amount but did not specify an amount',
        )
        self.assertEqual(due_before, iac.amount_due())
        self.assertFalse(
            Record.objects.filter(user=student, program=self.program, event=rt).exists(),
            'extra_costs_done Record must not be created on invalid custom amount',
        )
