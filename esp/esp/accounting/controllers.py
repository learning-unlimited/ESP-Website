
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

import logging
logger = logging.getLogger(__name__)

from esp.accounting.models import Transfer, Account, FinancialAidGrant, LineItemType, LineItemOptions
from esp.accounting import ReconciliationError, DuplicatePaymentError
from esp.program.models import FinancialAidRequest, Program, SplashInfo
from esp.users.models import ESPUser
from esp.utils.query_utils import nest_Q

from django.db import transaction
from django.db.models import Sum, Q
from django.template.defaultfilters import slugify

from decimal import Decimal


class BaseAccountingController(object):

    def default_source_account(self):
        return Account.objects.get(name='receivable')

    def default_finaid_account(self):
        return Account.objects.get(name='grants')

class GlobalAccountingController(BaseAccountingController):

    def setup_accounts(self):
        result = []
        default_accounts = [
            ('receivable', 'Accounts Receivable\nAll money coming from the outside is routed through here'),
            ('payable', 'Accounts Payable\nAll money leaving the organization is routed through here'),
            ('grants', 'Financial Aid Grants\nThis account is the source of financial aid transfers'),
        ]
        for account_info in default_accounts:
            (account, created) = Account.objects.get_or_create(name=account_info[0], description=account_info[1])
            result.append(account)
        return result

class ProgramAccountingController(BaseAccountingController):
    def __init__(self, program, *args, **kwargs):
        self.program = program

    def clear_all_data(self):
        #   Clear all financial data for the program
        FinancialAidGrant.objects.filter(request__program=self.program).delete()
        self.all_transfers().delete()
        self.get_lineitemtypes().delete()
        self.all_accounts().delete()

    def setup_accounts(self):
        #   For now, just create a single account for the program.  In the
        #   future we may want finer grained accounting per program.
        program = self.program
        (account, created) = Account.objects.get_or_create(name=slugify(program.name), description='Main account', program_id=program.id)
        return account

    def setup_lineitemtypes(self, base_cost, optional_items=None, select_items=None):
        result = []
        program = self.program

        #   optional_items is list of 3-tuples: (item name, cost, max quantity)
        if optional_items is None:
            optional_items = ()

        #   select_items is list of 2-tuples: (item name, [(choice 1 name, choice 1 cost), (choice 2 name, choice 2 cost), ...])
        if select_items is None:
            select_items = ()

        (lit_required, created) = LineItemType.objects.get_or_create(
            text='Program admission',
            amount_dec=Decimal('%.2f' % base_cost),
            required=True,
            max_quantity=1,
            program=program,
            for_payments=False
        )
        result.append(lit_required)

        (lit_payments, created) = LineItemType.objects.get_or_create(
            text='Student payment',
            program=program,
            for_payments=True
        )
        result.append(lit_payments)

        (lit_finaid, created) = LineItemType.objects.get_or_create(
            text='Financial aid grant',
            program=program,
            for_finaid=True
        )
        result.append(lit_finaid)

        (lit_sibling, created) = LineItemType.objects.get_or_create(
            text='Sibling discount',
            program=program,
            for_finaid=True
        )
        result.append(lit_sibling)

        for item in optional_items:
            (lit_optional, created) = LineItemType.objects.get_or_create(
                text=item[0],
                amount_dec=Decimal('%.2f' % item[1]),
                required=False,
                max_quantity=item[2],
                program=program,
                for_payments=False
            )
            result.append(lit_optional)

        for item in select_items:
            (lit_select, created) = LineItemType.objects.get_or_create(
                text=item[0],
                required=False,
                max_quantity=1,
                program=program,
            )
            for option in item[1]:
                (lio, created) = LineItemOptions.objects.get_or_create(
                lineitem_type=lit_select,
                description=option[0],
                amount_dec=option[1]
                )
            result.append(lit_select)

        return result

    def default_program_account(self):
        return Account.objects.filter(program=self.program).order_by('id')[0]

    def default_payments_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_payments=True).order_by('-id')[0]

    def default_finaid_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_finaid=True, text='Financial aid grant').order_by('-id')[0]

    def default_siblingdiscount_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_finaid=True, text='Sibling discount').order_by('-id')[0]

    def get_lineitemtypes_Q(self, required_only=False, optional_only=False, payment_only=False, lineitemtype_id=None):
        if lineitemtype_id:
            return Q(id=lineitemtype_id)
        q_object = Q(program=self.program)
        if required_only:
            q_object &= Q(required=True, for_payments=False, for_finaid=False)
        elif optional_only:
            q_object &= Q(required=False, for_payments=False, for_finaid=False)
            # The Stripe module (or, if used, donation module) currently takes care of the donation
            # optional line item, so ignore it in the optional costs module.
            for module_name in ['CreditCardModule_Stripe', 'DonationModule']:
                other_module = self.program.getModule(module_name)
                if other_module and other_module.get_setting('offer_donation', default=True):
                    q_object &= ~Q(text=other_module.get_setting('donation_text'))
        elif payment_only:
            q_object &= Q(required=False, for_payments=True, for_finaid=False)
        return q_object

    def get_lineitemtypes(self, **kwargs):
        qs = LineItemType.objects.filter(self.get_lineitemtypes_Q(**kwargs))
        return qs.order_by('text', '-id').distinct('text')

    def all_transfers_Q(self, **kwargs):
        """
        Returns a Q object that applies all wanted constraints on the related
        line_item objects.
        """
        q_object = self.get_lineitemtypes_Q(**kwargs)
        return nest_Q(q_object, 'line_item')

    def all_transfers(self, **kwargs):
        # Avoids a subquery by constructing a Q object, in all_transfers_Q(),
        # that applies all the wanted constraints on the related line_item
        # objects.
        return Transfer.objects.filter(self.all_transfers_Q(**kwargs)).distinct()

    def all_students_Q(self, **kwargs):
        """
        The students we want to query have registered for this program and have
        a transfer object that has the constraints we want.
        """
        q_object = self.all_transfers_Q(**kwargs)
        return Q(studentregistration__section__parent_class__parent_program=self.program) & nest_Q(q_object, 'transfer')

    def all_students(self, **kwargs):
        # Avoids a subquery by constructing a Q object, in all_students_Q(),
        # that applies all the wanted constraints on the related transfer
        # objects.
        return ESPUser.objects.filter(self.all_students_Q(**kwargs)).distinct()

    def all_accounts(self):
        return Account.objects.filter(program=self.program)

    def payments_summary(self):
        """ Return a tuple with the number and total dollar amount of payments
            that have been made so far. """
        payment_li_type = self.default_payments_lineitemtype()
        payments = Transfer.objects.filter(line_item=payment_li_type)
        return (payments.count(), payments.aggregate(total=Sum('amount_dec'))['total'])

    def classify_transfer(self, transfer):
        """Give a short human-readable description of a transfer.

        Given a transfer, return a short human-readable phrase describing
        the type of the transfer."""

        line_item = transfer.line_item
        if line_item == self.default_payments_lineitemtype():
            return 'Payment'
        elif line_item == self.default_finaid_lineitemtype():
            return 'Financial aid'
        elif line_item == self.default_siblingdiscount_lineitemtype():
            return 'Sibling discount'
        elif transfer.destination == self.default_program_account():
            req_desc = "required" if line_item.required else "optional"
            return "Cost ({})".format(req_desc)
        else:
            return 'Unrelated!?'

class IndividualAccountingController(ProgramAccountingController):
    def __init__(self, program, user, *args, **kwargs):
        super(IndividualAccountingController, self).__init__(program, *args, **kwargs)
        self.user = user

    def transfers_to_program_exist(self):
        return Transfer.objects.filter(
                destination=self.default_program_account(),
                user=self.user).exists()

    def ensure_required_transfers(self):
        """ Function to ensure there are transfers for this user corresponding
            to required line item types, e.g. program admission """

        program_account = self.default_program_account()
        source_account = self.default_source_account()
        required_line_items = self.get_lineitemtypes(required_only=True)

        existing_transfers_by_li = {t.line_item_id: t for t in Transfer.objects.filter(
            user=self.user, line_item__in=required_line_items)}

        for item in required_line_items:
            transfer = existing_transfers_by_li.get(item.id)
            if transfer is None:
                # A Transfer for this Line Item Type does not exist.
                # Create it now.
                Transfer.objects.create(source=source_account,
                                        destination=program_account,
                                        user=self.user,
                                        line_item=item,
                                        amount_dec=item.amount_dec)
            elif transfer.paid_in:
                # A Transfer for this Line Item Type already exists
                # *and* has already been paid. It's too late, so do
                # nothing.
                pass
            elif transfer.amount_dec == item.amount_dec:
                # A Transfer for this Line Item Type already exists
                # *and* has the correct amount. No changes are
                # necessary.
                pass
            else:
                # Adjust the amount of the Transfer to match the new
                # value.
                transfer.amount_dec = item.amount_dec
                transfer.save()

    def apply_preferences(self, optional_items):
        """ Function to ensure there are transfers for this user corresponding
            to optional line item types, accoring to their preferences.
            optional_items is a list of 4-tuples: (item name, quantity, cost, option ID)
            The last 2 items, cost and option ID, are non-required and should
            be set to None if unused.   """

        result = []
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        line_items = self.get_lineitemtypes(optional_only=True)

        #   Clear existing transfers
        Transfer.objects.filter(user=self.user, line_item__in=line_items).delete()

        #   Create transfers for optional line item types
        for item_tup in optional_items:
            (item_name, quantity, cost, option_id) = item_tup
            matched = False
            for lit in line_items:
                if lit.text == item_name:
                    matched = True
                    option = None
                    #   Determine the cost to apply to the transfer:
                    #   - Default to the cost of the line item type
                    transfer_amount = lit.amount_dec
                    #   - If a dollar amount is specified, use that amount
                    #     (note: this will override any line item option)
                    if cost is not None:
                        transfer_amount = cost
                    #   - If a line item option is specified, use its amount
                    #     (which may inherit from the line item type)
                    if option_id is not None:
                        option = LineItemOptions.objects.get(id=option_id)
                        if cost is None:
                            transfer_amount = option.amount_dec_inherited
                    for i in range(quantity):
                        result.append(Transfer.objects.create(source=source_account, destination=program_account, user=self.user, line_item=lit, amount_dec=transfer_amount, option=option))
                    break
            if not matched:
                raise Exception('Could not find a line item type matching "%s"' % item_name)

        return result

    def set_preference(self, lineitem_name, quantity, amount=None, option_id=None):
        #   Sets a single preference, after removing any exactly matching transfers.
        line_item = self.get_lineitemtypes().get(text=lineitem_name)
        option = None
        if amount is not None and option_id:
            self.get_transfers().filter(line_item=line_item, amount_dec=amount, option__id=option_id).delete()
        elif option_id:
            self.get_transfers().filter(line_item=line_item, option__id=option_id).delete()
            #   Pull the amount from the line item options, if it has one
            option = LineItemOptions.objects.get(id=option_id)
            if option.amount_dec is not None:
                amount = option.amount_dec
            else:
                amount = line_item.amount_dec
        elif amount is not None:
            self.get_transfers().filter(line_item=line_item, amount_dec=amount).delete()
        else:
            self.get_transfers().filter(line_item=line_item).delete()
            amount = line_item.amount_dec

        result = []
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        for i in range(quantity):
            result.append(Transfer.objects.create(source=source_account, destination=program_account, user=self.user, line_item=line_item, amount_dec=amount, option=option))

        return result

    def get_transfers(self, line_items=None, **kwargs):
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        if line_items is None:
            line_items = self.get_lineitemtypes(**kwargs)
        return Transfer.objects.filter(user=self.user, line_item__in=line_items).order_by('id')

    def get_preferences(self, line_items=None):
        #   Return a list of 4-tuples: (item name, quantity, cost, options)
        result = []
        transfers = self.get_transfers(line_items, optional_only=True)
        for transfer in transfers:
            li_name = transfer.line_item.text
            if (li_name, transfer.amount_dec, transfer.option_id) not in map(lambda x: (x[0], x[2], x[3]), result):
                result.append([li_name, 0, transfer.amount_dec, transfer.option_id])
                result_index = len(result) - 1
            else:
                result_index = map(lambda x: (x[0], x[2], x[3]), result).index((li_name, transfer.amount_dec, transfer.option_id))
            result[result_index][1] += 1
        return result

    ##  Functions to turn a user's account status for a program into a string
    ##  and to recover their account status from such a string

    def get_id(self):
        return '%d/%d' % (self.program.id, self.user.id)

    def get_identifier(self):
        #   A brief string containing information about the user and
        #   which purchases are included at this time
        purchases_str = ';'.join(['%d,%.2f' % (t.line_item_id, t.amount) for t in self.get_transfers()])
        return '%s:%s' % (self.get_id(), purchases_str)

    @staticmethod
    def from_id(id):
        sections = id.split('/')
        program = Program.objects.get(id=sections[0])
        user = ESPUser.objects.get(id=sections[1])
        return IndividualAccountingController(program, user)

    @staticmethod
    def program_from_identifier(identifier):
        id_str = identifier.split('/')[0]
        return Program.objects.get(id=int(id_str))

    @staticmethod
    @transaction.atomic
    def record_payment_from_identifier(identifier, amount_paid, transaction_id='',
                                       trusted=False):
        """
        Records a payment described by an identifier generated by
        get_identifier, validating that the identifier is well-formed and
        consistent with the database.

        If the amount (or program) of a Transfer was changed between the time
        the identifier was generated and when this method is invoked, an
        exception will be raised. This means that changing the cost of an item
        while users are paying will lead to errors.

        For identifiers that were passed through trusted (e.g. signed) channels,
        set trusted=True. The cost of Transfer objects will be automatically
        adjusted to match the amount saved in the identifier, removing the need
        for manual intervention in the above case.
        """
        # Parse identifier
        id_str, transfer_list = identifier.split(':')
        iac = IndividualAccountingController.from_id(id_str)

        payment = iac.submit_payment(
            amount_paid, transaction_id, link_transfers=False)

        # Reconcile Transfers with what's listed in the identifier. Note that
        # any exception will roll back the entire transaction.
        transfer_total = 0
        for item in transfer_list.split(';'):
            line_item_id, saved_amount = item.split(',')
            transfer = Transfer.objects.get(
                user=iac.user,
                line_item__id=int(line_item_id),
            )

            # This case is rare, since it's unusual to change the program of a
            # Line Item Type after it's been created.
            if transfer.line_item.program != iac.program:
                raise ReconciliationError(
                    "Failed on processing Transfer %d: program changed" % transfer.id)

            # Check for duplicate payment
            if transfer.paid_in:
                raise DuplicatePaymentError(
                    "Failed on processing Transfer %d: already paid" % transfer.id)

            # Check to see if the amount changed
            if '%.2f' % transfer.amount != saved_amount:
                if trusted:
                    transfer.amount = float(saved_amount)
                else:
                    msg = "Failed on processing Transfer %d: amount changed while " + \
                          "user was paying. The user was billed $%s for this item " + \
                          "and paid, but the item is now $%.2f"
                    raise ReconciliationError(
                        msg % (transfer.id, saved_amount, transfer.amount))

            # Mark as paid!
            transfer.paid_in = payment
            transfer_total += transfer.amount
            transfer.save()

        if transfer_total != amount_paid:
            raise ReconciliationError(
                "Failed to process payment. Item prices sum to $%.2f, but the user paid $%.2f" %
                (transfer_total, amount_paid))

        # Success!
        return payment

    def set_finaid_params(self, dollar_amount, discount_percent):
        #   Get the user's financial aid request or create one if it doesn't exist
        requests = FinancialAidRequest.objects.filter(user=self.user, program=self.program)
        if requests.exists():
            request = requests.order_by('-id')[0]
        else:
            request = FinancialAidRequest.objects.create(user=self.user, program=self.program, extra_explaination='Request automatically generated by accounting system')

        #   Create or modify a corresponding grant with the discount set to 100%
        (grant, created) = FinancialAidGrant.objects.get_or_create(request=request)
        if dollar_amount:
            grant.amount_max_dec = Decimal('%.2f' % dollar_amount)
        grant.percent = discount_percent
        grant.save()

    def grant_full_financial_aid(self):
        self.set_finaid_params(None, 100)

    def revoke_financial_aid(self):
        FinancialAidGrant.objects.filter(request__user=self.user, request__program=self.program).delete()

    def requested_transfers(self, ensure_required=True):
        if ensure_required:
            self.ensure_required_transfers()
        return Transfer.objects.filter(user=self.user, destination=self.default_program_account())

    def amount_requested(self, ensure_required=True):
        #   Compute sum of all transfers into program that are for this user
        amount_request = self.requested_transfers(ensure_required).aggregate(Sum('amount_dec'))['amount_dec__sum']
        if amount_request is not None:
            return amount_request
        else:
            return Decimal('0')

    def latest_finaid_grant(self):
        if FinancialAidGrant.objects.filter(request__user=self.user, request__program=self.program).exists():
            return FinancialAidGrant.objects.get(request__user=self.user, request__program=self.program)
        else:
            return None

    def amount_finaid(self, amount_requested=None, amount_siblingdiscount=None):
        if amount_requested is None:
            amount_requested = self.amount_requested()
        if amount_siblingdiscount is None:
            amount_siblingdiscount = self.amount_siblingdiscount()

        aid_amount = Decimal('0')
        latest_grant = self.latest_finaid_grant()
        if latest_grant is not None:
            if latest_grant.amount_max_dec is not None:
                if amount_requested - amount_siblingdiscount > latest_grant.amount_max_dec:
                    aid_amount = latest_grant.amount_max_dec
                else:
                    aid_amount = amount_requested - amount_siblingdiscount

            if latest_grant.percent is not None:
                discount_aid_amount = (Decimal('0.01') * latest_grant.percent) * (amount_requested - amount_siblingdiscount - aid_amount)
                aid_amount += discount_aid_amount

        return aid_amount

    def amount_siblingdiscount(self):
        if (not self.program.sibling_discount) or self.program.splashinfo_objects.get(self.user.id):
            return self.program.sibling_discount
        else:
            return Decimal('0')

    def amount_paid(self):
        #   Compute sum of all transfers from outside (e.g. credit card payments) that are for this user
        if Transfer.objects.filter(user=self.user, line_item=self.default_payments_lineitemtype(), source__isnull=True).exists():
            amount_paid = Transfer.objects.filter(user=self.user, line_item=self.default_payments_lineitemtype(), source__isnull=True).aggregate(Sum('amount_dec'))['amount_dec__sum']
        else:
            amount_paid = Decimal('0')
        return amount_paid

    def has_paid(self, in_full=False):
        if in_full:
            return (self.amount_paid() > 0) and (self.amount_due() <= 0)
        else:
            return (self.amount_paid() > 0)

    def amount_due(self):
        amt_request = self.amount_requested()
        amt_sibling = self.amount_siblingdiscount()
        return amt_request - self.amount_finaid(amt_request, amt_sibling) - amt_sibling - self.amount_paid()

    @transaction.atomic
    def submit_payment(self, amount, transaction_id='', link_transfers=True):
        """ Create a Transfer representing the user's payment for this program.
        By default, runs link_paid_transfers in an attempt to automatically
        create paid_in links. With link_transfers=False, this task is the
        responsibility of the caller. """

        line_item_type = self.default_payments_lineitemtype()
        target_account = self.default_source_account()
        payment = Transfer.objects.create(source=None,
                                          destination=target_account,
                                          user=self.user,
                                          line_item=line_item_type,
                                          amount_dec=Decimal('%.2f' % amount),
                                          transaction_id=transaction_id)
        if link_transfers:
            self.link_paid_transfers(payment)
        return payment

    @transaction.atomic
    def link_paid_transfers(self, payment):
        """ Given a Transfer representing a payment (e.g. a credit card
        payment), find all of the Transfers representing the items that were
        paid for and add a link back to the payment. """

        # Filter out Transfers representing payments, financial aid grants, and
        # purchasable items that have already been paid for.
        outstanding_transfers = self.get_transfers().filter(
            line_item__for_payments=False,
            line_item__for_finaid=False,
            paid_in__isnull=True,
        ).order_by('id')

        # Find the paid transfers by examining Transfers in order of creation
        # until they sum to the given amount.
        total = 0
        target = payment.get_amount()

        for transfer in outstanding_transfers:
            total += transfer.get_amount()
            transfer.paid_in = payment
            transfer.save()
            if total >= target:
                break

        if total != target:
            # This will cause all changes to be rolled back
            raise ValueError("Transfers do not sum to target: %.2f" % target)

    @staticmethod
    def updatePaid(program, user, paid=True):
        """ Create an invoice for the user and, if paid is True, create a receipt showing
        that they have paid all of the money they owe for the program. """
        iac = IndividualAccountingController(program, user)
        if not iac.has_paid():
            iac.ensure_required_transfers()
            if paid:
                iac.submit_payment(iac.amount_due())

    def __unicode__(self):
        return 'Accounting for %s at %s' % (self.user.name(), self.program.niceName())
