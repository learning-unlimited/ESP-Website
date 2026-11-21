
from __future__ import absolute_import
from __future__ import unicode_literals
import six
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
from django.utils import timezone

from decimal import Decimal

class LineItemType(models.Model):
    text = models.TextField(help_text='A description of this line item.')
    amount_dec = models.DecimalField(default=0, max_digits=9, decimal_places=2, help_text='The cost of this line item.')
    program = models.ForeignKey(Program)
    required = models.BooleanField(default=False)
    max_quantity = models.PositiveIntegerField(default=1)
    for_payments = models.BooleanField(default=False)
    for_finaid = models.BooleanField(default=False, help_text='Should financial aid cover this line item?')
    onsite_only = models.BooleanField(default=False, help_text='Only sold at the help desk on the day of the program; hidden from the student extra costs page.')
    helpdesk_amount_dec = models.DecimalField(
        max_digits=9, decimal_places=2, blank=True, null=True,
        help_text='Price at the help desk on the day of the program, if different from the price above.')

    @property
    def helpdesk_price(self):
        """ What the help desk charges for this item (without an option). """
        return self.amount_dec if self.helpdesk_amount_dec is None else self.helpdesk_amount_dec

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
        return self.lineitemoptions_set.all().values_list('id', 'amount_dec', 'description', 'is_custom').order_by('-is_custom')

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
        """ Return a ($min, $max) tuple of what this line item's options cost
            (each option's own amount, or this item's amount if it doesn't set
            one), or None if there are no fixed-price options. Options where
            the user enters their own amount (is_custom) are left out; see
            has_custom_options. """
        prices = [option.amount_dec_inherited for option in self.lineitemoptions_set.all()
                  if not option.is_custom]
        if not prices:
            return None
        return (min(prices), max(prices))

    def __str__(self):
        if self.amount_dec:
            return six.u('%s for %s ($%s)') % (self.text, self.program, self.amount_dec)
        else:
            return six.u('%s for %s') % (self.text, self.program)

    class Meta:
        ordering = ('-program_id',)

class LineItemOptions(models.Model):
    lineitem_type = models.ForeignKey(LineItemType)
    description = models.TextField(help_text='You can include the cost as part of the description, which is helpful if the cost differs from the line item type.')
    amount_dec = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, help_text='The cost of this option--leave blank to inherit from the line item type.')
    is_custom = models.BooleanField(default=False, help_text='Should the student be allowed to specify a custom amount for this option?')
    helpdesk_amount_dec = models.DecimalField(
        max_digits=9, decimal_places=2, blank=True, null=True,
        help_text='Price of this option at the help desk on the day of the program; leave blank to use the line item type\'s help desk price, or else this option\'s regular price.')

    class Meta:
        # Otherwise Django pluralizes the class name to "line item optionss".
        verbose_name = 'line item option'

    @property
    def helpdesk_price(self):
        """ What the help desk charges for this option: its own help desk
        price, else the line item type's, else its regular price. """
        if self.helpdesk_amount_dec is not None:
            return self.helpdesk_amount_dec
        if self.lineitem_type.helpdesk_amount_dec is not None:
            return self.lineitem_type.helpdesk_amount_dec
        return self.amount_dec_inherited

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

    def __str__(self):
        return '%s ($%s)' % (self.description, self.amount_dec)

class FinancialAidGrant(models.Model):
    request = AjaxForeignKey(FinancialAidRequest)
    amount_max_dec = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, help_text='Enter a number here to grant a dollar value of financial aid.  The grant will cover this amount or the full cost, whichever is less.')
    percent = models.PositiveIntegerField(blank=True, null=True, help_text='Enter an integer between 0 and 100 here to grant a certain percentage discount after the above dollar credit is applied.  0 means no additional discount, 100 means no payment is required for items that are covered by financial aid.')
    timestamp = models.DateTimeField(auto_now=True)
    finalized = models.BooleanField(default=False, editable=False)
    #   Who granted it (blank for grants made before this was recorded); see
    #   Transfer.recorded_by for what these mean
    granted_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+',
                                on_delete=models.SET_NULL, editable=False)

    @property
    def amount_max(self):
        if self.amount_max_dec is None:
            return None
        else:
            return float(self.amount_max_dec)

    @property
    def terms(self):
        """ Short description of the grant, e.g. '100%', 'up to $40.00',
        'up to $40.00 + 50%'. A $0.00 cap or 0% counts as not set. """
        parts = []
        if self.amount_max_dec and self.percent != 100:
            parts.append('up to $%.2f' % self.amount_max_dec)
        if self.percent:
            parts.append('%d%%' % self.percent)
        return ' + '.join(parts) or 'nothing'

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

        #   Save first: amount_finaid() looks the grant up from the database,
        #   so an unsaved grant (as created by FinancialAidRequest.approve())
        #   would otherwise be recorded as $0.00, and unsaved edits ignored.
        self.save()

        from esp.accounting.controllers import IndividualAccountingController
        iac = IndividualAccountingController(self.program, self.user)
        source_account = iac.default_finaid_account()
        dest_account = iac.default_source_account()
        line_item_type = iac.default_finaid_lineitemtype()

        (transfer, created) = Transfer.objects.update_or_create(source=source_account, destination=dest_account, user=self.user, line_item=line_item_type, defaults={'amount_dec': iac.amount_finaid()})
        self.finalized = True
        self.save()
        return transfer

    def __str__(self):
        if self.percent and self.amount_max_dec:
            return 'Grant %s (max $%s, %d%% discount) at %s' % (self.user, self.amount_max_dec, self.percent, self.program)
        elif self.percent:
            return 'Grant %s (%d%% discount) at %s' % (self.user, self.percent, self.program)
        elif self.amount_max_dec:
            return 'Grant %s (max $%s) at %s' % (self.user, self.amount_max_dec, self.program)
        else:
            return 'Grant %s (no aid specified) at %s' % (self.user, self.program)

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

    def __str__(self):
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
    #   For payments (transfers from outside): how it was paid. Blank for
    #   transfers that aren't payments.
    PAYMENT_METHOD_CHOICES = (
        ('card', 'Credit card'),
        ('cash_check', 'Cash or check'),
    )
    payment_method = models.CharField(max_length=20, blank=True, default='', choices=PAYMENT_METHOD_CHOICES)
    #   Who recorded it: the real account behind the request (an admin morphed
    #   into another account counts as the admin).
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+',
                                 on_delete=models.SET_NULL)
    #   For a payment that checking the student in implied (they paid their
    #   balance in cash or check at check-in): that check-in record. Undoing
    #   the check-in deletes the payment; deleting the record any other way
    #   (admin, or with its program) keeps the money record, unlinked.
    checkin_record = models.ForeignKey(
        'users.Record', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='checkin_payments')

    def set_amount(self, amount):
        if self.paid_in:
            raise Exception('Cannot change the amount of this transfer since it was already paid')
        self.amount_dec = Decimal('%.2f' % amount)
    def get_amount(self):
        return float(self.amount_dec)
    amount = property(get_amount, set_amount)

    def __str__(self):
        return 'Transfer $%s from %s to %s' % (self.amount_dec, self.source, self.destination)

class OnsiteSale(models.Model):
    """ An anonymous sale at the help desk on the day of the program (e.g. a
    non-preordered shirt or a plushie), not tied to any account. Recording
    cash sales is optional; card sales and sales that get a receipt are always
    recorded. A sale with no lines is a custom amount (see description). """
    METHOD_CHOICES = (
        ('cash_check', 'Cash or check'),
        ('card', 'Credit card'),
    )
    STATUS_CHOICES = (
        ('pending', 'Waiting for card payment'),
        ('paid', 'Paid'),
        ('review', 'Paid the wrong amount (treasury to check)'),
        ('void', 'Void'),
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payer_name = models.CharField(max_length=200, blank=True, default='')
    description = models.CharField(max_length=200, blank=True, default='',
                                   help_text='What a custom-amount sale was for.')
    total_dec = models.DecimalField(max_digits=9, decimal_places=2)
    transaction_id = models.CharField(max_length=64, blank=True, default='')
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    voided_at = models.DateTimeField(blank=True, null=True)
    voided_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)

    class Meta:
        ordering = ('-id',)

    def identifier(self):
        """ What we send CyberSource to pay for this sale; see
        esp.program.views.submit_transaction. """
        return '%d/onsite-%d:%.2f' % (self.program_id, self.id, self.total_dec)

    def __str__(self):
        return 'Help desk sale %d ($%.2f, %s)' % (self.id, self.total_dec, self.status)

class OnsiteSaleLine(models.Model):
    sale = models.ForeignKey(OnsiteSale, on_delete=models.CASCADE, related_name='lines')
    line_item = models.ForeignKey(LineItemType, on_delete=models.PROTECT)
    option = models.ForeignKey(LineItemOptions, blank=True, null=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price_dec = models.DecimalField(max_digits=9, decimal_places=2,
                                         help_text='The help desk price when it was sold.')

    @property
    def amount_dec(self):
        return self.unit_price_dec * self.quantity

class DayOfCardCheckout(models.Model):
    """ A card payment started at day-of troubleshooting (for a student's
    balance) or the help desk (for a sale), on the laptop or by QR code: who
    started which charge, and why if it was below the card minimum. """
    CHANNEL_CHOICES = (
        ('laptop', 'On the staff laptop'),
        ('qr', 'On the payer\'s phone (QR code)'),
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    user = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='dayof_card_checkouts',
                          on_delete=models.CASCADE)
    sale = models.ForeignKey(OnsiteSale, blank=True, null=True, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    identifier = models.TextField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    custom_amount = models.BooleanField(default=False)
    description = models.CharField(max_length=200, blank=True, default='')
    below_minimum_reason = models.CharField(max_length=200, blank=True, default='')
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class Receipt(models.Model):
    """ A receipt handed out on the day of the program, for a student's
    account (from day-of troubleshooting) or a help desk sale. What was
    printed is frozen in lines_json, so a reprint is identical. Receipts can
    be voided but never edited. """
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    number = models.PositiveIntegerField(help_text='Counts up within the program.')
    user = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='dayof_receipts', on_delete=models.CASCADE)
    sale = models.ForeignKey(OnsiteSale, blank=True, null=True, related_name='receipts', on_delete=models.CASCADE)
    payer_name = models.CharField(max_length=200, blank=True, default='')
    lines_json = models.TextField()
    issued_at = models.DateTimeField(auto_now_add=True)
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    voided_at = models.DateTimeField(blank=True, null=True)
    voided_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)

    class Meta:
        unique_together = (('program', 'number'),)
        ordering = ('-id',)

    def __str__(self):
        return 'Receipt %d for %s' % (self.number, self.program)

class HelpdeskPriceChange(models.Model):
    """ A change to a help desk price, made on the help desk prices page. """
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    line_item = models.ForeignKey(LineItemType, on_delete=models.CASCADE)
    option = models.ForeignKey(LineItemOptions, blank=True, null=True, on_delete=models.CASCADE)
    #   Blank means "not set" (the item fell back to another price)
    old_amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    new_amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-timestamp',)

class CybersourcePostback(models.Model):
    """ Logs every Cybersource postback to enable debugging and automated
        reconciliation."""
    STATUS_CHOICES = (
        ('processed', 'Processed'),
        ('needs_review', 'Payment recorded; needs manual review'),
        ('not_paid', 'No payment (declined, cancelled, or error)'),
        ('review_hold', 'Held for review by the processor; may have been charged'),
        ('failed', 'Failed; payment not recorded'),
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    post_data = models.TextField()
    transfer = models.ForeignKey(Transfer, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, blank=True, default='', choices=STATUS_CHOICES,
                              help_text='Blank for postbacks received before statuses were recorded.')
    transaction_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    #   Who and what the postback was for, from its identifier, so a postback
    #   can be traced even when no payment was recorded for it
    user = AjaxForeignKey(ESPUser, blank=True, null=True, on_delete=models.SET_NULL)
    program = models.ForeignKey(Program, blank=True, null=True, on_delete=models.SET_NULL)
    status_detail = models.TextField(blank=True, default='',
                                     help_text='Why the postback needs attention, if it does.')
    #   For a help desk sale (identifier <program>/onsite-<sale id>)
    onsite_sale = models.ForeignKey(OnsiteSale, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return '%d' % self.id

class PaymentIssueResolution(models.Model):
    """ Treasury's note about a payment issue listed on a program's credit
    card viewer page (see esp.accounting.payment_issues): a problem postback
    or an overpaid student that was dealt with, or a payment recorded by hand
    there. Reopening an issue keeps its resolution, marked reopened; resolving
    it again adds a new one. """
    KIND_CHOICES = (
        ('postback', 'Problem postback'),
        ('overpayment', 'Overpaid student'),
        ('manual_payment', 'Payment recorded by hand'),
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    #   The problem postback, for kind 'postback'
    postback = models.ForeignKey(CybersourcePostback, blank=True, null=True,
                                 on_delete=models.CASCADE, related_name='resolutions')
    #   The payment recorded by hand, if one was (kind 'manual_payment', or a
    #   'postback' resolved by recording its payment)
    transfer = models.ForeignKey(Transfer, blank=True, null=True, on_delete=models.SET_NULL,
                                 related_name='+')
    #   The student and program the issue is about (for a postback, copied from
    #   it; both blank for a postback that couldn't be linked to anyone)
    user = AjaxForeignKey(ESPUser, blank=True, null=True, on_delete=models.SET_NULL)
    program = models.ForeignKey(Program, blank=True, null=True, on_delete=models.SET_NULL)
    #   For an overpaid student, how much they were overpaid by when this was
    #   resolved (the issue reopens by itself if that amount changes); for a
    #   postback or payment, the amount paid
    amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    note = models.TextField()
    resolved_by = models.ForeignKey(ESPUser, blank=True, null=True, on_delete=models.SET_NULL,
                                    related_name='+')
    resolved_at = models.DateTimeField(default=timezone.now)
    reopened_by = models.ForeignKey(ESPUser, blank=True, null=True, on_delete=models.SET_NULL,
                                    related_name='+')
    reopened_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['resolved_at', 'id']

    def __str__(self):
        if self.kind == 'postback':
            return 'Postback %s resolved %s' % (self.postback_id, self.resolved_at)
        if self.kind == 'manual_payment':
            return 'Payment of %s for %s recorded by hand %s' % (self.amount, self.user, self.resolved_at)
        return 'Overpayment of %s by %s resolved %s' % (self.amount, self.user, self.resolved_at)

def install():
    """Set up the default accounts."""
    logger.info("Installing esp.accounting initial data...")
    from esp.accounting.controllers import GlobalAccountingController
    gac = GlobalAccountingController()
    gac.setup_accounts()
