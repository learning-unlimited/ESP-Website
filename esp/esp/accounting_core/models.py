
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.db import models, transaction
from django.db.models import Q
from django.contrib.auth.models import User
from esp.datatree.models import DataTree, GetNode
from esp.db.fields import AjaxForeignKey
from esp.db.models.prepared import ProcedureManager

from datetime import datetime

class AccountingException(Exception):
    pass

class CompletedTransactionException(AccountingException):
    pass

class EmptyTransactionException(AccountingException):
    pass

class LineItemTypeManager(ProcedureManager):
    def forProgram(self, program):
        """ Get all LineItemTypes (currently including optional ones) for the given program. """
        a = GetNode(program.anchor.get_uri()+'/LineItemTypes')
        return self.filter(anchor__rangestart__gte=a.rangestart, anchor__rangeend__lte=a.rangeend)

class LineItemType(models.Model):
    """ A set of default values for a line item """
    text = models.TextField() # description of line item
    amount = models.FloatField(help_text='This should be negative for student costs charged to a program.', max_digits=9, decimal_places=2, default=0.0) # default amount
    anchor = AjaxForeignKey(DataTree,related_name='accounting_lineitemtype',null=True) # account to post the line item
    finaid_amount = models.FloatField(max_digits=9, decimal_places=2, default=0.0) # amount after financial aid
    finaid_anchor = AjaxForeignKey(DataTree,null=True,related_name='accounting_finaiditemtype')
    
    objects = LineItemTypeManager()
    
    def __str__(self):
        if self.anchor: url = self.anchor.get_uri()
        else: url = 'NULL'
        return "LineItemType: %s (%.02f or %.02f for %s)" % (self.text, self.amount, self.finaid_amount, url)

    class Admin:
        pass

class Balance(models.Model):
    """ A posted balance for an account.  This serves the purpose of keeping
        transactions from collecting ad infinitum on a ledger, so the entire
        history of a ledger need not be explored to determine the balance on
        that ledger. """
    anchor = AjaxForeignKey(DataTree, related_name='balance')
    user = AjaxForeignKey(User, related_name='balance')
    timestamp = models.DateTimeField()
    amount = models.FloatField(max_digits=16, decimal_places=2)
    past = models.ForeignKey('self', null=True)

    def __unicode__(self):
        return u'Balance for %s in %s as of %s: %14.02f' % (self.user, str(self.anchor), str(self.timestamp), self.amount)

    class Admin:
        pass

    class Meta:
        order_with_respect_to = 'anchor'
        ordering = ['-timestamp']

    @staticmethod
    def get_current_balance(anchor, user=None, li_type=None):
        # Determine the set of prevously posted balances
        q = Q(anchor=anchor, past__isnull=True)
        if user is not None:
            q = q & Q(user=user)
        bals = Balance.objects.filter(q)

        # Calculate the total posted balance on the account
        bal_start = sum([bal.amount for bal in bals])

        # Find the pending line items that apply to the account
        q = Q(transaction__complete=True, posted_to__isnull=True, anchor=anchor)
        if user is not None: q = q & Q(user=user)
        if li_type is not None: q = q & Q(li_type=li_type)
        items = LineItem.objects.filter(q)

        # Total the pending line items
        bal_items = sum([li.amount for li in items])

        # Operation Complete!
        return (bal_start + bal_items, bal_start, bal_items, bals, items)

    @classmethod
    def _post_balance_slave(klass, anchor, user, li_set, bal_last):
        bal = klass.objects.create(anchor=anchor, user=user, amount=0.0, past=bal_last, timestamp=datetime.now())
        li_set = [li for li in li_set if li.user == user]
        bal_items = sum([li.amount for li in li_set])
        bal.amount = bal_items + bal_last.amount
        bal.save()
        for li in li_set:
            li.posted_to = bal
            li.save()
        return bal

    @classmethod
    @transaction.commit_on_success
    def post_balance(klass, anchor, user=None):
        q = Q(anchor=anchor,posted_to__isnull=True)
        if user is not None: q = q & Q(user=user)
        li_set = LineItem.objects.filter(q)
        u_set = set([li.user for li in li_set])
        bal_set = []
        for user in u_set:
            bal_last = klass.objects.filter(anchor=anchor,past__isnull=True,user=user)
            if bal_last: bal_last = bal_last[0]
            else: bal_last = None
            bal = klass._post_balance_slave( anchor, user, li_set, bal_last )
            bal_set.append(bal)
        return bal_set


class Transaction(models.Model):
    """ A double-ledger accounting transaction """
    timestamp = models.DateTimeField()
    text = models.TextField()
    complete = models.BooleanField(default=False)

    def __str__(self):
        if self.complete: completion = ''
        else: completion = ' (INCOMPLETE)'
        return "T-%u (%s): %s" % (self.id, str(self.timestamp), self.text + completion)

    class Admin:
        pass

    @classmethod
    def begin(klass,anchor,text,reference=None):
        """ Create a new transaction """
        t = klass()
        t.anchor = anchor
        t.text = text
        t.timestamp = datetime.now()
        t.complete = False
        t.reference = reference
        t.save()

        # Operation Complete!
        return t

    @transaction.commit_on_success
    def add_item(self, user, li_type, finaid=False, amount=None, text=None, anchor=None):
        """ Add a line item to this transaction. Note that positive amounts on program accounts indicate an expense to the organization, and negative amounts indicate income to the organization. This condition is reversed for asset accounts. """
        if self.complete: raise CompletedTransactionException

        li = LineItem()
        li.transaction = self

        if anchor is None: anchor = li_type.anchor
        li.anchor = anchor

        if amount is None:
            amount = li_type.amount
            if finaid and (li_type.finaid_amount != amount):
                finaid_amount = li_type.finaid_amount - amount

                fa_li = LineItem()
                fa_li.transaction = self
                fa_li.anchor = li_type.finaid_anchor
                fa_li.amount = finaid_amount
                fa_li.user = user
                fa_li.li_type, unused = LineItemType.objects.get_or_create(text='Financial Aid', defaults={'amount': 0.0, 'anchor': GetNode("Q"), 'finaid_amount': 0.0, 'finaid_anchor': GetNode("Q") })
                fa_li.text = fa_li.li_type.text
                fa_li.save()

        li.amount = amount
        li.user = user
        if text is None: text = li_type.text
        li.text = text
        li.li_type = li_type
        li.save()

        # Operation Complete!
        return li

    def get_balance(self):
        items = self.lineitem_set.all()
        if items.count() == 0: raise EmptyTransactionException
        amounts = [li.amount for li in items]
        return -sum(amounts)

    @transaction.commit_on_success
    def post_balance(self, user, text, anchor):
        """ Post a transaction balance to an account and complete the transaction. """
        if self.complete: raise CompletedTransactionException

        balance = self.get_balance()
        li_type, unused = LineItemType.objects.get_or_create(text='Balance Posting', defaults={'amount': 0.0, 'anchor': GetNode("Q"), 'finaid_amount': 0.0, 'finaid_anchor': GetNode("Q") })

        li = LineItem()
        li.transaction = self
        li.anchor = anchor
        li.amount = balance
        li.user = user
        li.text = text
        li.li_type = li_type
        li.save()

        self.complete = True
        self.save()

        return li

class LineItemManager(ProcedureManager):
    def forProgram(self, program):
        """ Get all LineItems (currently including optional ones) whose types are anchored in the given program. """
        a = GetNode(program.anchor.get_uri()+'/LineItemTypes')
        return self.filter(li_type__anchor__rangestart__gte=a.rangestart, li_type__anchor__rangeend__lte=a.rangeend)

class LineItem(models.Model):
    """ A transaction line item """
    transaction = models.ForeignKey(Transaction)
    user = AjaxForeignKey(User,related_name='accounting_lineitem')
    anchor = AjaxForeignKey(DataTree,related_name='accounting_lineitem')
    amount = models.FloatField(max_digits=9, decimal_places=2)
    text = models.TextField()
    li_type = models.ForeignKey(LineItemType)
    posted_to = models.ForeignKey(Balance, null=True)
    
    objects = LineItemManager()

    def __str__(self):
        return "L-%u (T-%u): %.02f %s - %s, %s" % (self.id, self.transaction.id, self.amount, self.anchor.uri, self.user.username, self.text)

    class Admin:
        pass
