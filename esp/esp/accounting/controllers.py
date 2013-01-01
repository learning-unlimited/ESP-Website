
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
  Email: web-team@lists.learningu.org
"""

from esp.accounting.models import Transfer, Account, FinancialAidGrant, LineItemType
from esp.program.models import FinancialAidRequest, Program, SplashInfo
from esp.users.models import ESPUser

from django.db.models import Sum
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

    def setup_accounts(self):
        #   For now, just create a single account for the program.  In the
        #   future we may want finer grained accounting per program.
        program = self.program
        (account, created) = Account.objects.get_or_create(name=slugify(program.name), description='Main account for %s' % program.niceName(), program=program)
        return account

    def setup_lineitemtypes(self, base_cost, optional_items=None):
        result = []
        program = self.program

        #   optional_items is list of 3-tuples: (item name, cost, max quantity)
        if optional_items is None:
            optional_items = ()
            
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
        return result

    def default_program_account(self):
        return Account.objects.filter(program=self.program).order_by('id')[0]
    
    def default_payments_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_payments=True).order_by('-id')[0]
    
    def default_finaid_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_finaid=True, text='Financial aid grant').order_by('-id')[0]

    def default_siblingdiscount_lineitemtype(self):
        return LineItemType.objects.filter(program=self.program, for_finaid=True, text='Sibling discount').order_by('-id')[0]

    def get_lineitemtypes(self, required_only=False, optional_only=False, payment_only=False):
        if required_only:
            qs = LineItemType.objects.filter(program=self.program, required=True, for_payments=False, for_finaid=False)
        elif optional_only:
            qs = LineItemType.objects.filter(program=self.program, required=False, for_payments=False, for_finaid=False)
        elif payment_only:
            qs = LineItemType.objects.filter(program=self.program, required=False, for_payments=True, for_finaid=False) 
        else:
            qs = LineItemType.objects.filter(program=self.program)
            
        return qs.order_by('text', '-id').distinct('text')

    def all_transfers(self, **kwargs):
        return Transfer.objects.filter(line_item__in=self.get_lineitemtypes(**kwargs))

    def execute_pending_transfers(self):
        pass


class IndividualAccountingController(ProgramAccountingController):
    def __init__(self, program, user, *args, **kwargs):
        super(IndividualAccountingController, self).__init__(program, *args, **kwargs)
        self.user = user

    def add_required_transfers(self):
        """ Function to ensure there are transfers for this user corresponding
            to required line item types, e.g. program admission """

        result = []
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        line_items = self.get_lineitemtypes(required_only=True)

        #   Clear existing transfers
        Transfer.objects.filter(user=self.user, line_item__in=line_items, executed=False).delete()

        #   Create transfers for required line item types
        for lit in line_items:
            result.append(Transfer.objects.create(source=source_account, destination=program_account, user=self.user, line_item=lit, amount_dec=lit.amount_dec))
        return result

    def apply_preferences(self, optional_items):
        """ Function to ensure there are transfers for this user corresponding
            to optional line item types, accoring to their preferences.
            optional_items is a list of 3-tuples: (item name, quantity, cost option) """

        result = []
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        line_items = self.get_lineitemtypes(optional_only=True)

        #   Clear existing transfers
        Transfer.objects.filter(user=self.user, line_item__in=line_items, executed=False).delete()

        #   Create transfers for optional line item types
        for item in optional_items:
            matched = False
            for lit in line_items:
                if lit.text == item[0]:
                    matched = True
                    for i in range(item[1]):
                        if item[2] != 0:
                            result.append(Transfer.objects.create(source=source_account, destination=program_account, user=self.user, line_item=lit, amount_dec=item[2]))
                    break
            if not matched:
                raise Exception('Could not find a line item type matching "%s"' % item[0])

        return result

    def set_preference(self, lineitem_name, quantity, amount=None):
        #   Sets a single preference
        line_item = self.get_lineitemtypes().get(text=lineitem_name)
        if amount:
            self.get_transfers().filter(line_item=line_item, amount_dec=amount).delete()
        else:
            self.get_transfers().filter(line_item=line_item).delete()
            amount = line_item.amount_dec

        result = []
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        for i in range(quantity):
            result.append(Transfer.objects.create(source=source_account, destination=program_account, user=self.user, line_item=line_item, amount_dec=amount))
        return result

    def get_transfers(self, **kwargs):
        program_account = self.default_program_account()
        source_account = self.default_source_account()
        line_items = self.get_lineitemtypes(**kwargs)
        return Transfer.objects.filter(user=self.user, line_item__in=line_items).order_by('id')

    def get_preferences(self):
        #   Return a list of 3-tuples: (item name, quantity, cost option)
        result = []
        transfers = self.get_transfers(optional_only=True)
        for transfer in transfers:
            li_name = transfer.line_item.text
            if (li_name, transfer.amount_dec) not in map(lambda x: (x[0], x[2]), result):
                result.append([li_name, 0, transfer.amount_dec])
                result_index = len(result) - 1
            else:
                result_index = map(lambda x: (x[0], x[2]), result).index((li_name, transfer.amount_dec))
            result[result_index][1] += 1
        return result

    ##  Functions to turn a user's account status for a program into a string
    ##  and to recover their account status from such a string

    def get_id(self):
        return '%d/%d' % (self.program.id, self.user.id)

    def get_identifier(self):
        #   A brief string containing information about the user and 
        #   which purchases are included at this time
        purchases_str = ';'.join(['%d,%.2f' % (t.line_item.id, t.amount) for t in self.get_transfers()])
        return '%s:%s' % (self.get_id(), purchases_str)

    @staticmethod
    def from_id(id):
        sections = id.split('/')
        program = Program.objects.get(id=sections[0])
        user = ESPUser.objects.get(id=sections[1])
        return IndividualAccountingController(program, user)

    @staticmethod
    def from_identifier(identifier):
        #   Parse string
        sections = identifier.split(':')
        transfer_strings = sections[1].split(';')
        iac = IndividualAccountingController.from_id(sections[0])
        transfer_list = iac.get_transfers()
        if len(transfer_strings) != len(transfer_list):
            print 'Warning, expected %d transfers for this program/user but got %d; not checking transfers for consistency' % (iac.get_transfers().count(), len(transfer_strings))
            return iac
        for i in range(len(transfer_strings)):
            t = transfer_list[i]
            if transfer_strings[i] != '%d,%.2f' % (t.line_item.id, t.amount):
                print 'Warning, inconsistent transfer: expected "%s", got "%s"' % ((t.line_item.id, t.amount), transfer_strings[i])
        return iac

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

    def amount_requested(self):
        self.add_required_transfers()
        program_account = self.default_program_account()
        
        #   Compute sum of all transfers into program that are for this user
        if Transfer.objects.filter(user=self.user, destination=program_account).exists():
            amount_requested = Transfer.objects.filter(user=self.user, destination=program_account).aggregate(Sum('amount_dec'))['amount_dec__sum']
        else:
            amount_requested = Decimal('0')
        
        return amount_requested
    
    def amount_finaid(self, amount_requested=None):
        if amount_requested is None:
            amount_requested = self.amount_requested()

        aid_amount = Decimal('0')
        if FinancialAidGrant.objects.filter(request__user=self.user, request__program=self.program).exists():
            latest_grant = FinancialAidGrant.objects.get(request__user=self.user, request__program=self.program)
            print 'Applying financial aid for %s at %s' % (self.user.name(), self.program.niceName())

            if latest_grant.amount_max_dec is not None:
                print '-- Aid ceiling: %s' % latest_grant.amount_max_dec
                if amount_requested > latest_grant.amount_max_dec:
                    aid_amount = latest_grant.amount_max_dec
                    print '   Aid updated to %s' % aid_amount
                else:
                    aid_amount = amount_requested
                    print '   Aid updated to %s (equal to amount due)'

            if latest_grant.percent is not None:
                print '-- Discount percentage: %s%%' % latest_grant.percent
                discount_aid_amount = (Decimal('0.01') * latest_grant.percent) * (amount_requested - aid_amount)
                aid_amount += discount_aid_amount
                print '   Aid updated to %s' % aid_amount

        return aid_amount
    
    def amount_siblingdiscount(self):
        #   Hard-coded $20 discount for now; could be made into a Tag in the future
        if SplashInfo.objects.filter(program=self.program, student=self.user, siblingdiscount=True).exists():
            return Decimal('20.00')
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
            return (self.amount_paid() > 0) and (self.amount_due <= 0)
        else:
            return (self.amount_paid() > 0)

    def amount_due(self):
        amt_request = self.amount_requested()
        return amt_request - self.amount_finaid(amt_request) - self.amount_siblingdiscount() - self.amount_paid()

    def clear_payments(self):
        #   Remove all payments listed for this user at this program
        line_item_type = self.default_payments_lineitemtype()
        target_account = self.default_source_account()
        Transfer.objects.filter(source=None, destination=target_account, user=self.user, line_item=line_item_type).delete()

    def submit_payment(self, amount):
        #   Create a transfer representing a user's payment for this program
        line_item_type = self.default_payments_lineitemtype()
        target_account = self.default_source_account()
        return Transfer.objects.create(source=None, destination=target_account, user=self.user, line_item=line_item_type, amount_dec=Decimal('%.2f' % amount))

    def __unicode__(self):
        return 'Accounting for %s at %s' % (self.user.name(), self.program.niceName())
    

