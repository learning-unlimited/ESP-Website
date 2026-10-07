
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
from esp.accounting.cybersource import compute_signature
from esp.middleware      import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from decimal import Decimal
from datetime import datetime, timezone
import uuid

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

    def isCompleted(self, user=None):
        """ Whether the user has fully paid for this program. """
        user = self._resolve_user(user)
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
        tag_value = Tag.getProgramTag('creditcard_required_for_extracosts', program=self.program, default='')
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

        if not self.isStep():
            raise ESPError("The Cybersource module is not configured")

        # Sign the outgoing form so that the resulting postback to
        # submit_transaction can be authenticated (see
        # esp.accounting.cybersource). Every field below that is actually
        # rendered into the payment form must be listed in
        # signed_field_names, in the same order used here, or verification
        # will fail.
        context['access_key'] = settings.CYBERSOURCE_CONFIG['access_key']
        context['profile_id'] = settings.CYBERSOURCE_CONFIG['profile_id']
        context['transaction_uuid'] = uuid.uuid4().hex
        context['signed_date_time'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        context['comments'] = '%s Invoice %s/%s (for %s)' % (
            settings.ORGANIZATION_SHORT_NAME, self.program.id, user.id, self.program.niceName())

        signed_fields = {
            'access_key': context['access_key'],
            'profile_id': context['profile_id'],
            'transaction_uuid': context['transaction_uuid'],
            'signed_date_time': context['signed_date_time'],
            'merchant_id': context['merchant_id'],
            'amount': '%.2f' % context['itemizedcosttotal'],
            'merchantDefinedData1': context['identifier'],
            'comments': context['comments'],
            'billTo_country': 'US',
        }
        context['signed_field_names'] = ','.join(signed_fields.keys())
        context['unsigned_field_names'] = ''
        context['signature'] = compute_signature(
            signed_fields, context['signed_field_names'],
            settings.CYBERSOURCE_CONFIG['secret_key'])

        return render_to_response(self.baseDir() + 'cardpay.html', request, context)

    def isStep(self):
        config = settings.CYBERSOURCE_CONFIG
        return bool(config['post_url'] and config['merchant_id']
                    and config['access_key'] and config['profile_id']
                    and config['secret_key'])

    class Meta:
        proxy = True
        app_label = 'modules'
