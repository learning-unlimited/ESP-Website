
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call, meets_cap
from esp.program.modules import module_ext
from esp.utils.web       import render_to_response
from datetime            import datetime
from django.conf         import settings
from django.db.models.query     import Q
from esp.users.models    import ESPUser
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.middleware      import ESPError
from esp.middleware.threadlocalrequest import get_current_request

class CreditCardModule_Cybersource(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card Payment Module (Cybersource)",
            "link_title": "Credit Card Payment",
            "module_type": "learn",
            "seq": 10000,
            "choosable": 2,
            }

    def isCompleted(self):
        """ Whether the user has paid for this program or its parent program. """
        return IndividualAccountingController(self.program, get_current_request().user).has_paid()
    have_paid = isCompleted

    def students(self, QObject = False):
        #   This query represented students who have a payment transfer from the outside
        pac = ProgramAccountingController(self.program)
        QObj = Q(transfer__source__isnull=True, transfer__line_item=pac.default_payments_lineitemtype())

        if QObject:
            return {'creditcard': QObj}
        else:
            return {'creditcard':ESPUser.objects.filter(QObj).distinct()}

    def studentDesc(self):
        return {'creditcard': """Students who have filled out the credit card form"""}

    @main_call
    @needs_student
    @meets_deadline('/Payment')
    @meets_cap
    def cybersource(self, request, tl, one, two, module, extra, prog):

        # Force users to pay for non-optional stuffs
        user = request.user

        iac = IndividualAccountingController(self.program, request.user)
        context = {}
        context['module'] = self
        context['one'] = one
        context['two'] = two
        context['tl']  = tl
        context['user'] = user
        context['contact_email'] = self.program.director_email
        context['invoice_id'] = iac.get_id()
        context['identifier'] = iac.get_identifier()
        payment_type = iac.default_payments_lineitemtype()
        sibling_type = iac.default_siblingdiscount_lineitemtype()
        grant_type = iac.default_finaid_lineitemtype()
        context['itemizedcosts'] = iac.get_transfers().exclude(line_item__in=[payment_type, sibling_type, grant_type]).order_by('-line_item__required')
        context['itemizedcosttotal'] = iac.amount_due()
        context['subtotal'] = iac.amount_requested()
        context['financial_aid'] = iac.amount_finaid()
        context['sibling_discount'] = iac.amount_siblingdiscount()
        context['amount_paid'] = iac.amount_paid()
        context['result'] = request.GET.get("result")
        context['post_url'] = settings.CYBERSOURCE_CONFIG['post_url']
        context['merchant_id'] = settings.CYBERSOURCE_CONFIG['merchant_id']

        if (not context['post_url']) or (not context['merchant_id']):
            raise ESPError("The Cybersource module is not configured")

        return render_to_response(self.baseDir() + 'cardpay.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
