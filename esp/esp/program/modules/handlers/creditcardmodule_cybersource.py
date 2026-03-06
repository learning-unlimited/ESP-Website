
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
from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, meets_deadline, main_call, meets_cap
from esp.utils.web       import render_to_response
from django.conf         import settings
from django.db.models.query     import Q
from esp.users.models    import ESPUser
from esp.tagdict.models  import Tag
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.middleware      import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from decimal import Decimal

class CreditCardModule_Cybersource(ProgramModuleObj):
    doc = """Accept credit card payments via Cybersource."""

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
        """ Whether the user has fully paid for this program. """
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return IndividualAccountingController(self.program, user).has_paid(in_full=True)
    have_paid = isCompleted

    def isRequired(self):
        """Conditionally require credit card payment when student selects extra cost items.

        Same logic as CreditCardModule_Stripe.isRequired(). See that class
        for full documentation of the 'creditcard_required_for_extracosts' tag.
        """
        if super(CreditCardModule_Cybersource, self).isRequired():
            return True
        return self._extracost_requires_payment()

    def _extracost_requires_payment(self):
        """Check if the student selected extra cost items that require CC payment."""
        from esp.accounting.models import Transfer
        tag_value = Tag.getTag('creditcard_required_for_extracosts', self.program, default='')
        if not tag_value:
            return False
        request = get_current_request()
        user = getattr(self, 'user', request.user if request else None)
        if not user or not user.is_authenticated:
            return False
        iac = IndividualAccountingController(self.program, user)
        if iac.amount_due() < Decimal('0.50'):
            return False
        pac = ProgramAccountingController(self.program)
        extra_lits = pac.get_lineitemtypes(include_donations=False).exclude(
            text__in=pac.admission_items)
        if tag_value.strip() != '*':
            item_names = [name.strip() for name in tag_value.split(',')]
            extra_lits = extra_lits.filter(text__in=item_names)
        return Transfer.objects.filter(
            user=user, line_item__in=extra_lits,
        ).exists()

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
    @needs_student_in_grade
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

    def isStep(self):
        return settings.CYBERSOURCE_CONFIG['post_url'] and settings.CYBERSOURCE_CONFIG['merchant_id']

    class Meta:
        proxy = True
        app_label = 'modules'
