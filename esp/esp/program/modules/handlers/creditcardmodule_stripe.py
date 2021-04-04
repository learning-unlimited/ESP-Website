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
from esp.utils.web import render_to_response
from esp.dbmail.models import send_mail
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.accounting.models import LineItemType
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.modules.handlers.donationmodule import DonationModule

from django.conf import settings
from django.db import transaction
from django.db.models.query import Q
from django.http import HttpResponseRedirect
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from decimal import Decimal
from datetime import datetime
import stripe
import json
import re

class CreditCardModule_Stripe(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card Payment Module (Stripe)",
            "link_title": "Credit Card Payment",
            "module_type": "learn",
            "seq": 10000,
            "choosable": 0,
            }

    def apply_settings(self):
        #   Rather than using a model in module_ext.*, configure the module
        #   from a Tag (which can be per-program or global), combining the
        #   Tag's specifications with defaults in the code.
        DEFAULTS = {
            'offer_donation': True,
            'donation_text': 'Donation to Learning Unlimited',
            'donation_options': [10, 20, 50],
            'invoice_prefix': settings.INSTITUTION_NAME.lower(),
        }
        DEFAULTS.update(settings.STRIPE_CONFIG)
        tag_data = json.loads(Tag.getProgramTag('stripe_settings', self.program))
        self.settings = DEFAULTS.copy()
        self.settings.update(tag_data)
        return self.settings

    def get_setting(self, name, default=None):
        return self.apply_settings().get(name, default)

    def line_item_type(self):
        pac = ProgramAccountingController(self.program)
        (donate_type, created) = pac.get_lineitemtypes().get_or_create(program=self.program, text=self.get_setting('donation_text'))
        return donate_type

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

    def check_setup(self):
        """ Validate the keys specified in the stripe_settings Tag.
            If something is wrong, provide an error message which will hopefully
            only be seen by admins during setup. """

        self.apply_settings()

        #   Check for a 'donation' line item type on this program, which we will need
        #   Note: This could also be created by default for every program,
        #   in the accounting controllers.
        if self.settings['offer_donation']:
            (lit, created) = LineItemType.objects.get_or_create(
                text=self.settings['donation_text'],
                program=self.program,
                required=False
            )

        #   A Stripe account comes with 4 keys, starting with e.g. sk_test_
        #   and followed by a 24 character base64-encoded string.
        valid_pk_re = r'pk_(test|live)_([A-Za-z0-9+/=]){24}'
        valid_sk_re = r'sk_(test|live)_([A-Za-z0-9+/=]){24}'
        if not re.match(valid_pk_re, self.settings['publishable_key']) or not re.match(valid_sk_re, self.settings['secret_key']):
            raise ESPError('The site has not yet been properly set up for credit card payments. Administrators should contact the <a href="mailto:{{settings.SUPPORT}}">websupport team to get it set up.', True)

    @main_call
    @needs_student
    @meets_deadline('/Payment')
    @meets_cap
    def payonline(self, request, tl, one, two, module, extra, prog):

        #   Check that the user has completed all required modules so that they
        #   are "finished" registering for the program.  (In other words, they
        #   should be registered for at least one class, and filled out other
        #   required forms, before paying by credit card.)
        modules = prog.getModules(request.user, tl)
        completedAll = True
        for module in modules:
            if not module.isCompleted() and module.required:
                completedAll = False
        if not completedAll and not request.user.isAdmin(prog):
            raise ESPError("Please go back and ensure that you have completed all required steps of registration before paying by credit card.", log=False)

        #   Check for setup of module.  This is also required to initialize settings.
        self.check_setup()

        user = request.user

        iac = IndividualAccountingController(self.program, request.user)
        context = {}
        context['module'] = self
        context['program'] = prog
        context['user'] = user
        context['invoice_id'] = iac.get_id()
        context['identifier'] = iac.get_identifier()
        payment_type = iac.default_payments_lineitemtype()
        sibling_type = iac.default_siblingdiscount_lineitemtype()
        grant_type = iac.default_finaid_lineitemtype()
        offer_donation = self.settings['offer_donation']
        donate_type = iac.get_lineitemtypes().get(text=self.settings['donation_text']) if offer_donation else None
        context['itemizedcosts'] = iac.get_transfers().exclude(line_item__in=filter(None, [payment_type, sibling_type, grant_type, donate_type])).order_by('-line_item__required')
        context['itemizedcosttotal'] = iac.amount_due()
        #   This amount should be formatted as an integer in order to be
        #   accepted by Stripe.
        context['totalcost_cents'] = int(context['itemizedcosttotal'] * 100)
        context['subtotal'] = iac.amount_requested()
        context['financial_aid'] = iac.amount_finaid()
        context['sibling_discount'] = iac.amount_siblingdiscount()
        context['amount_paid'] = iac.amount_paid()

        #   Load donation amount separately, since the client-side code needs to know about it separately.
        donation_prefs = iac.get_preferences([donate_type,]) if offer_donation else None
        if donation_prefs:
            context['amount_donation'] = Decimal(donation_prefs[0][2])
            context['has_donation'] = True
            context['form'] = DonationModule.get_form(settings=self.settings, donation_initial=context['amount_donation'])
        else:
            context['amount_donation'] = Decimal('0.00')
            context['has_donation'] = False
            context['form'] = DonationModule.get_form(settings=self.settings, donation_initial=None)
        context['amount_without_donation'] = context['itemizedcosttotal'] - context['amount_donation']

        if 'HTTP_HOST' in request.META:
            context['hostname'] = request.META['HTTP_HOST']
        else:
            context['hostname'] = Site.objects.get_current().domain
        context['institution'] = settings.INSTITUTION_NAME
        context['support_email'] = settings.DEFAULT_EMAIL_ADDRESSES['support']


        return render_to_response(self.baseDir() + 'cardpay.html', request, context)

    def send_error_email(self, request, context):
        """ Send an email to admins explaining the credit card error.
            (Broken out from charge_payment view for readability.) """

        context['request'] = request
        context['program'] = self.program
        context['postdata'] = request.POST.copy()
        domain_name = Site.objects.get_current().domain
        msg_content = render_to_string(self.baseDir() + 'error_email.txt', context)
        msg_subject = '[ ESP CC ] Credit card error on %s: %d %s' % (domain_name, request.user.id, request.user.name())
        # This message could contain sensitive information.  Send to the
        # confidential messages address, and don't bcc the archive list.
        send_mail(msg_subject, msg_content, settings.SERVER_EMAIL, [self.program.getDirectorConfidentialEmail()], bcc=None)

    @aux_call
    @needs_student
    def charge_payment(self, request, tl, one, two, module, extra, prog):
        #   Check for setup of module.  This is also required to initialize settings.
        self.check_setup()

        context = {'postdata': request.POST.copy()}

        group_name = Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)

        iac = IndividualAccountingController(self.program, request.user)

        #   Set donation transfer
        form = None
        if request.method == 'POST':

            current_donation_prefs = iac.get_preferences([self.line_item_type(), ])
            if current_donation_prefs:
                current_donation = Decimal(iac.get_preferences([self.line_item_type(), ])[0][2])
            else:
                current_donation = None
            form = DonationModule.get_form(settings=self.settings, donation_initial=current_donation, form_data=request.POST)

            if form.is_valid():
                #   Clear the Transfers by specifying quantity 0
                iac.set_preference('Donation to Learning Unlimited', 0)
                if form.amount:
                    iac.set_preference('Donation to Learning Unlimited', 1, amount=form.amount)

        #   Set Stripe key based on settings.  Also require the API version
        #   which our code is designed for.
        stripe.api_key = self.settings['secret_key']
        # We are using the 2014-03-13 version of the Stripe API, which is
        # v1.12.2.
        stripe.api_version = '2014-03-13'

        if request.POST.get('ponumber', '') != iac.get_id():
            #   If we received a payment for the wrong PO:
            #   This is not a Python exception, but an error nonetheless.
            context['error_type'] = 'inconsistent_po'
            context['error_info'] = {'request_po': request.POST.get('ponumber', ''), 'user_po': iac.get_id()}

        if 'error_type' not in context:
            #   Check the amount in the POST against the amount in our records.
            #   If they don't match, raise an error.
            amount_cents_post = Decimal(request.POST['totalcost_cents'])
            amount_cents_iac = Decimal(iac.amount_due()) * 100
            if amount_cents_post != amount_cents_iac:
                context['error_type'] = 'inconsistent_amount'
                context['error_info'] = {
                    'amount_cents_post': amount_cents_post,
                    'amount_cents_iac':  amount_cents_iac,
                }

        if 'error_type' not in context:
            try:
                with transaction.atomic():
                    # Save a record of the charge if we can uniquely identify the user/program.
                    # If this causes an error, the user will get a 500 error
                    # page, and the card will NOT be charged.
                    # If an exception is later raised by
                    # stripe.Charge.create(), then the transaction will be
                    # rolled back.
                    # Thus, we will never be in a state where the card has been
                    # charged without a record being created on the site, nor
                    # vice-versa.
                    totalcost_dollars = Decimal(request.POST['totalcost_cents']) / 100

                    #   Create a record of the transfer without the transaction ID.
                    transfer = iac.submit_payment(totalcost_dollars, 'TBD')

                    # Create the charge on Stripe's servers - this will charge
                    # the user's card.
                    charge = stripe.Charge.create(
                        amount=amount_cents_post,
                        currency="usd",
                        card=request.POST['stripeToken'],
                        description="Payment for %s %s - %s" % (group_name, prog.niceName(), request.user.name()),
                        statement_descriptor=group_name[0:22], #stripe limits statement descriptors to 22 characters
                        metadata={
                            'ponumber': request.POST['ponumber'],
                        },
                    )

                    #   Now that the charge has been performed by Stripe, save its
                    #   transaction ID for our records.
                    transfer.transaction_id = charge.id
                    transfer.save()

            except stripe.error.CardError, e:
                context['error_type'] = 'declined'
                context['error_info'] = e.json_body['error']
            except stripe.error.InvalidRequestError, e:
                #   While this is a generic error meaning invalid parameters were supplied
                #   to Stripe's API, we will usually see it because of a duplicate request.
                context['error_type'] = 'invalid'
            except stripe.error.AuthenticationError, e:
                context['error_type'] = 'auth'
            except stripe.error.APIConnectionError, e:
                context['error_type'] = 'api'
            except stripe.error.StripeError, e:
                context['error_type'] = 'generic'

        if 'error_type' in context:
            #   If we got any sort of error, send an email to the admins and render an error page.
            self.send_error_email(request, context)
            return render_to_response(self.baseDir() + 'failure.html', request, context)

        #   Render the success page, which doesn't do much except direct back to studentreg.
        context['amount_paid'] = totalcost_dollars
        context['statement_descriptor'] = group_name[0:22]
        context['can_confirm'] = self.deadline_met('/Confirm')
        return render_to_response(self.baseDir() + 'success.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
