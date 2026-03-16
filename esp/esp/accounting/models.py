
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

from esp.users.models import ESPUser
from esp.program.models import Program, FinancialAidRequest
from esp.db.fields import AjaxForeignKey

from django.db import models
from django.db.models import Sum

from decimal import Decimal

class LineItemType(models.Model):
    text = models.TextField(help_text='A description of this line item.')
    amount_dec = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, help_text='The cost of this line item.')
    program = models.ForeignKey(Program)
    required = models.BooleanField(default=False)
    max_quantity = models.PositiveIntegerField(default=1)
    for_payments = models.BooleanField(default=False)
    for_finaid = models.BooleanField(default=False)

    @property
    def amount(self):
        if self.amount_dec is None:
            return None
        else:
            return float(self.amount_dec)

    @property
    def num_options(self):
        return self.lineitemoptions_set.all().count()

    @property
    def options(self):
        return self.lineitemoptions_set.all().values_list('id', 'amount_dec', 'description','is_custom').order_by('-is_custom')

    @property
    def has_custom_options(self):
        """ Return True if at least one of the options for this line item type
            allows a custom dollar amount to be entered.    """
        return self.lineitemoptions_set.filter(is_custom=True).exists()

    @property
    def option_choices(self):
        """ Return a list of (ID, description) tuples, one for each of the
            possible options.  Intended for use as form field choices.  """
        #   We can't use the 'options' property anymore since we need to compute the inherited amount.
        result = []
        for option in self.lineitemoptions_set.all():
            if option.is_custom:
                result.append((option.id, '%s -- enter amount below' % (option.description,)))
            else:
                result.append((option.id, '%s -- $%.2f' % (option.description, option.amount_dec_inherited)))
        return result

    @property
    def options_cost_range(self):
        """ Return a ($min, $max) tuple specifying the min and max cost of the
            possible options for this line item type, or None if there are no
            options.    """
        opts = list(self.options)
        if len(opts) == 0:
            return None
        else:
            min_cost = opts[0][1]
            max_cost = opts[-1][1]
            if min_cost is None:
                min_cost = self.amount_dec
            if max_cost is None:
                max_cost = self.amount_dec
            return (min_cost, max_cost)

    def __unicode__(self):
        if self.amount_dec:
            return u'%s for %s ($%s)' % (self.text, self.program, self.amount_dec)
        else:
            return u'%s for %s' % (self.text, self.program)

    class Meta:
        ordering = ('-program_id',)

class LineItemOptions(models.Model):
    lineitem_type = models.ForeignKey(LineItemType)
    description = models.TextField(help_text='You can include the cost as part of the description, which is helpful if the cost differs from the line item type.')
    amount_dec = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, help_text='The cost of this option--leave blank to inherit from the line item type.')
    is_custom = models.BooleanField(default=False, help_text='Should the student be allowed to specify a custom amount for this option?')

    @property
    def amount_dec_inherited(self):
        """ The amount to charge for this option; inherits from parent
            line item type if amount_dec is not set.    """
        if self.amount_dec is None:
            return self.lineitem_type.amount_dec
        else:
            return self.amount_dec

    @property
    def amount(self):
        if self.amount_dec is None:
            return None
        else:
            return float(self.amount_dec)

    def __unicode__(self):
        return u'%s ($%s)' % (self.description, self.amount_dec)

class FinancialAidGrant(models.Model):
    request = AjaxForeignKey(FinancialAidRequest)
    amount_max_dec = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, help_text='Enter a number here to grant a dollar value of financial aid.  The grant will cover this amount or the full cost, whichever is less.')
    percent = models.PositiveIntegerField(blank=True, null=True, help_text='Enter an integer between 0 and 100 here to grant a certain percentage discount after the above dollar credit is applied.  0 means no additional discount, 100 means no payment required.')
    timestamp = models.DateTimeField(auto_now=True)
    finalized = models.BooleanField(default=False, editable=False)

    @property
    def amount_max(self):
        if self.amount_max_dec is None:
            return None
        else:
            return float(self.amount_max_dec)

    @property
    def user(self):
        return self.request.user
    @property
    def program(self):
        return self.request.program

    def finalize(self):
        #   Create a transfer for the amount of this grant
        if self.finalized:
            return

        from esp.accounting.controllers import IndividualAccountingController
        iac = IndividualAccountingController(self.program, self.user)
        source_account = iac.default_finaid_account()
        dest_account = iac.default_source_account()
        line_item_type = iac.default_finaid_lineitemtype()

        (transfer, created) = Transfer.objects.get_or_create(source=source_account, destination=dest_account, user=self.user, line_item=line_item_type, amount_dec=iac.amount_finaid())
        self.finalized = True
        self.save()
        return transfer

    def __unicode__(self):
        if self.percent and self.amount_max_dec:
            return u'Grant %s (max $%s, %d%% discount) at %s' % (self.user, self.amount_max_dec, self.percent, self.program)
        elif self.percent:
            return u'Grant %s (%d%% discount) at %s' % (self.user, self.percent, self.program)
        elif self.amount_max_dec:
            return u'Grant %s (max $%s) at %s' % (self.user, self.amount_max_dec, self.program)
        else:
            return u'Grant %s (no aid specified) at %s' % (self.user, self.program)

    class Meta:
        unique_together = ('request',)

class Account(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    program = models.ForeignKey(Program, blank=True, null=True)

    @property
    def balance(self):
        result = 0
        if Transfer.objects.filter(source=self).exists():
            result -= Transfer.objects.filter(source=self).aggregate(Sum('amount_dec'))['amount_dec__sum']
        if Transfer.objects.filter(destination=self).exists():
            result += Transfer.objects.filter(destination=self).aggregate(Sum('amount_dec'))['amount_dec__sum']
        return result

    @property
    def pending_balance(self):
        return self.balance

    @property
    def description_title(self):
        return ''.join(self.description.split('\n')[:1])

    @property
    def description_contents(self):
        return '\n'.join(self.description.split('\n')[1:])

    def balance_breakdown(self):
        transfers_in = Transfer.objects.filter(destination=self).values('source').annotate(amount = Sum('amount_dec'))
        transfers_out = Transfer.objects.filter(source=self).values('destination').annotate(amount = Sum('amount_dec'))
        transfers_in_context = []
        transfers_out_context = []

        for transfer in transfers_in:
            target_name = "none"
            target_title = "External payer[s]"

            if transfer['source'] is not None:
                target = Account.objects.get(id=transfer['source'])
                target_name = target.name
                target_title = target.description_title

            transfers_in_context.append({'amount': transfer['amount'], 'target_type': 'source', 'target_name': target_name, 'target_title': target_title})

        for transfer in transfers_out:
            target_name = "none"
            target_title = "External payee[s]"

            if transfer['destination'] is not None:
                target = Account.objects.get(id=transfer['destination'])
                target_name = target.name
                target_title = target.description_title

            transfers_out_context.append({'amount': transfer['amount'], 'target_type': 'destination', 'target_name': target_name, 'target_title': target_title})

        return (transfers_out_context, transfers_in_context)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name',)

class Transfer(models.Model):
    source = models.ForeignKey(
        Account, blank=True, null=True, related_name='transfer_source',
        help_text='Source account; where the money is coming from. Leave blank if this is a payment from outside.')
    destination = models.ForeignKey(
        Account, blank=True, null=True, related_name='transfer_destination',
        help_text='Destination account; where the money is going to. Leave blank if this is a payment to an outsider.')
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    line_item = models.ForeignKey(LineItemType)
    option = models.ForeignKey(LineItemOptions, blank=True, null=True)
    amount_dec = models.DecimalField(max_digits=9, decimal_places=2)
    transaction_id = models.TextField(
        'Transaction ID', max_length=64, blank=True, default='',
        help_text='If this transfer is from a credit card transaction, stores the transaction ID number from the processor.')
    timestamp = models.DateTimeField(auto_now=True)
    paid_in = models.ForeignKey(
        'self', blank=True, null=True, on_delete=models.PROTECT,
        help_text='If this transfer is for a fee that has been paid, references the transfer for the payment transaction.')

    def set_amount(self, amount):
        if self.paid_in:
            raise Exception('Cannot change the amount of this transfer since it was already paid')
        self.amount_dec = Decimal('%.2f' % amount)
    def get_amount(self):
        return float(self.amount_dec)
    amount = property(get_amount, set_amount)

    def __unicode__(self):
        return u'Transfer $%s from %s to %s' % (self.amount_dec, self.source, self.destination)

class CybersourcePostback(models.Model):
    """ Logs every Cybersource postback to enable debugging and automated
        reconciliation."""
    timestamp = models.DateTimeField(auto_now_add=True)
    post_data = models.TextField()
    transfer = models.ForeignKey(Transfer, blank=True, null=True,
                                 on_delete=models.SET_NULL)

    def __unicode__(self):
        return u'%d' % self.id

def install():
    """Set up the default accounts."""
    logger.info("Installing esp.accounting initial data...")
    from esp.accounting.controllers import GlobalAccountingController
    gac = GlobalAccountingController()
    gac.setup_accounts()
