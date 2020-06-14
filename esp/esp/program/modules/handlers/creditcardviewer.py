
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web       import render_to_response
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from argcache            import cache_function

class CreditCardViewer(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card View Module",
            "link_title": "View Credit Card Transactions",
            "module_type": "manage",
            "seq": 10000,
            "choosable": 0,
            }

    @main_call
    @needs_admin
    def viewpay(self, request, tl, one, two, module, extra, prog):
        pac = ProgramAccountingController(prog)
        student_list = list(pac.all_students())
        payment_table = []

        #   Fetch detailed information for every student associated with the program
        for student in student_list:
            payment_table.append(self._payment_table_row_cached(prog, student))

        #   Also fetch summary information about the payments
        (num_payments, total_payment) = pac.payments_summary()

        context = {
            'program': prog,
            'payment_table': payment_table,
            'num_students': len(student_list),
            'num_payments': num_payments,
            'total_payment': total_payment,
        }

        return render_to_response(self.baseDir() + 'viewpay.html', request, context)

    @staticmethod
    @cache_function
    def _payment_table_row_cached(prog, student):
        iac = IndividualAccountingController(prog, student)
        return (student, iac.get_transfers(), iac.amount_requested(), iac.amount_due())
    _payment_table_row_cached.__func__.depend_on_model('accounting.LineItemType')
    _payment_table_row_cached.__func__.depend_on_model('accounting.LineItemOptions')
    _payment_table_row_cached.__func__.depend_on_model('accounting.FinancialAidGrant')
    _payment_table_row_cached.__func__.depend_on_model('accounting.Account')
    _payment_table_row_cached.__func__.depend_on_model('accounting.Transfer')

    class Meta:
        proxy = True
        app_label = 'modules'
