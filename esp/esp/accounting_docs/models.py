
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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
from django.db import models, transaction
from django.db.models import Q
from django.contrib.auth.models import User
from esp.datatree.models import *
from esp.db.fields import AjaxForeignKey
from esp.cache import cache_function
from esp.accounting_core.models import LineItemType, Balance, Transaction, LineItem, EmptyTransactionException, CompletedTransactionException
from esp.accounting_docs.checksum import Checksum
from esp.users.models import ESPUser
from datetime import datetime

from esp.middleware import ESPError_Log
from esp.accounting_core.models import Transaction

class MultipleDocumentError(ESPError_Log):
    pass

class Document(models.Model):
    """ A tracer for a transaction """

    TYPE_CHOICES=(
        (0, 'Journal'),
        (1, 'Correction'),
        (2, 'Invoice'),
        (3, 'Receipt'),
        (4, 'CC Authorization'),
        (5, 'CC Sale'),
        (6, 'Refund Authorization'),
        (7, 'Reimbursement Request'),
        (8, 'Green Form'),
        (9, 'Inventory')
    )

    # Document header
    anchor = AjaxForeignKey(DataTree)
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    txn = models.ForeignKey(Transaction)
    doctype = models.IntegerField(choices=TYPE_CHOICES)

    # Document workflow (creates next_set and prev_set)
    docs_next = models.ManyToManyField('self', symmetrical=False, related_name='docs_prev')

    # Document references
    locator = models.CharField(max_length=16, unique=True)
    cc_ref = models.TextField(blank=True,default='')

    # Tools
    _checksum = Checksum(rotors=2, base_length=8)
    

    def __unicode__(self):
        if self.txn.complete:
            complete_str = " (complete)"
        else:
            complete_str = ""

        choices_dict = dict(self.TYPE_CHOICES)
            
        return u"%s for %s on %s%s" % (choices_dict[self.doctype], str(self.user), str(self.anchor), complete_str)
    
    def set_default_locator(self):
        self.locator = Document._checksum.calculate(str(self.id))

    def get_locator(self):
        if self.locator == None or self.locator == '':
            self.set_default_locator()

        return self.locator

    @cache_function
    def get_DOCTYPE(user, anchor, li_types=[], dont_duplicate=False, finaid=None, get_complete=False, doctype=None):
        """ Create an "empty shopping cart" for a particular user in a particular
        anchor (i.e. program). Or find the cart when they already have one. """
        
        if finaid is None:
            finaid = ESPUser(user).hasFinancialAid(anchor)
        
        #   Put the documents in descending order of ID so, in case there is more than 1, the result is
        #   consistent from run to run.
        qs = Document.objects.filter(user=user, anchor=anchor, doctype=doctype, txn__complete=get_complete).order_by('-id').select_related().distinct()
        
        """ if qs.count() > 1:
            raise MultipleDocumentError, 'Found multiple uncompleted transactions for this user and anchor.'
        elif qs.count() == 1: """
        additional_invoice = False
        if qs.count() >= 1 and qs[0].txn.complete:
            for lit in li_types:
                #   If we're missing any line items, then we've got to make another invoice and return it.
                if (qs.count() >= 1) and (lit.id not in [a['li_type'] for a in qs[0].txn.lineitem_set.all().values('li_type')]):
                    additional_invoice = True
                    
        if qs.count() >= 1 and not additional_invoice:
            #   Retrieve the document, add on any line items that we received if necessary, and return.
            doc = qs[0]
            for lit in li_types:
                if not dont_duplicate or doc.txn.lineitem_set.filter(li_type=lit).count() == 0:
                    doc.txn.add_item(user, lit, finaid, anchor=anchor)
            return doc
        elif qs.count() < 1 and get_complete:
            raise MultipleDocumentError, 'Found no complete documents with the requested properties'
        else:
            #   Set up a new transaction and document with all of the requested line items.
            new_tx = Transaction.begin(anchor, 'User payments for %s: %s' % (anchor.parent.friendly_name, anchor.friendly_name))
            new_tx.save()
            for lit in li_types:
                if not dont_duplicate or new_tx.lineitem_set.filter(li_type=lit).count() == 0:
                    if qs.count() == 0:
                        new_tx.add_item(user, lit, finaid)
                    else:
                        #   If there's already an appropriate transaction but we're making a new one
                        if qs[0].txn.lineitem_set.filter(li_type=lit).count() == 0:
                            new_tx.add_item(user, lit, finaid)

            new_doc = Document()
            new_doc.txn = new_tx
            new_doc.anchor = anchor
            new_doc.doctype = doctype
            new_doc.user = user

            # Give a random locator to satisfy uniqueness constraint
            # (in case of race condition)
            from random import randint
            new_doc.locator = 'N/A:' + str(randint(0,9999999))

            new_doc.save()
            
            new_doc.set_default_locator()
            new_doc.save()
            
            return new_doc
    get_DOCTYPE.depend_on_row(lambda: Document, lambda doc: {'user': doc.user})
    get_DOCTYPE.depend_on_row(lambda: LineItem, lambda item: {'user': item.user})
    get_DOCTYPE = staticmethod(get_DOCTYPE)

    @classmethod
    def get_invoice(cls, user, anchor, li_types=[], dont_duplicate=False, finaid=None, get_complete=False):
        return cls.get_DOCTYPE(user, anchor, li_types=li_types, dont_duplicate=dont_duplicate, finaid=finaid, get_complete=get_complete, doctype=2)

    @classmethod
    def get_receipt(cls, user, anchor, li_types=[], dont_duplicate=False, finaid=None, get_complete=False):
        return cls.get_DOCTYPE(user, anchor, li_types=li_types, dont_duplicate=dont_duplicate, finaid=finaid, get_complete=get_complete, doctype=3)
    
    @cache_function
    def get_completed(user, anchor):
        return list(Document.objects.filter(user=user, anchor=anchor, txn__complete=True))
    #   This will be invalidated when a balance is posted to a transaction because doing so
    #   modifies line items associated with the transaction.
    get_completed.depend_on_row(lambda: Document, lambda doc: {'user': doc.user})
    get_completed.depend_on_row(lambda: LineItem, lambda item: {'user': item.user})
    get_completed = staticmethod(get_completed)

    @staticmethod
    def get_by_locator(loc):
        return Document.objects.get(locator=loc)

    @staticmethod
    def receive_creditcard(user, loc, amt, cc_id):
        """ Call this function when a successful credit card payment is received. """
        old_doc = Document.get_by_locator(loc)
        if old_doc.txn.complete:
            raise CompletedTransactionException
        
        new_tx = Transaction.begin(old_doc.anchor, 'Credit card payment')
        li_type, unused = LineItemType.objects.get_or_create(text='Credit Card Payment',anchor=GetNode("Q/Accounts/Receivable/OnSite"))
        new_tx.add_item(user, li_type, amount=-amt)
        
        new_doc = Document()
        new_doc.txn = new_tx
        new_doc.doctype = 3
        new_doc.anchor = old_doc.anchor
        new_doc.user = user
        new_doc.cc_ref = cc_id
        new_doc.save()
        
        new_doc.set_default_locator()
        new_doc.docs_prev.add(old_doc)
        new_doc.save()
        
        new_tx.post_balance(user, "Credit Card payment received", GetNode("Q/Accounts/Realized"))

        old_doc.txn.post_balance(user, "Credit Card payment received", GetNode("Q/Accounts/Receivable/OnSite"))
        old_doc.txn.save()

        return new_doc
    
    @staticmethod
    def prepare_onsite(user, loc):
        """ Call this function for all users that have registered online for a
        program.  It will close off all the online transactions and leave anticipated
        amounts in Accounts Receivable. """
        
        money_target = DataTree.get_by_uri('Q/Accounts/Receivable/OnSite', create=True)
        old_doc = Document.get_by_locator(loc)
        old_doc.txn.post_balance(user, 'Expecting on-site payment', money_target)
    
    @staticmethod
    def receive_onsite(user, loc, amt=None, ref=''):
        """ Call this function for each user that pays on-site.  If their initial
        invoice was not closed, you will need to call prepare_onsite first.
        The amount is assumed to be the balance of the user's obligations to ESP.
        An additional note can be supplied in the ref field, although this is normally
        used for Cybersource credit card transaction IDs. """
        
        money_src = DataTree.get_by_uri('Q/Accounts/Receivable/OnSite', create=True)
        money_target = DataTree.get_by_uri('Q/Accounts/Realized', create=True)
        
        old_doc = Document.get_by_locator(loc)

        if amt is None:
            amt = old_doc.cost(mask_receivable=True)

        new_tx = Transaction.begin(old_doc.anchor, 'On-site payment')
        li_type, unused = LineItemType.objects.get_or_create(text='Received on-site payment',anchor=money_src)
        new_tx.add_item(user, li_type, amount=-amt)
        
        try:
            new_doc = Document.get_receipt(user, old_doc.anchor)
        except:        
            new_doc = Document()
        
        new_doc.txn = new_tx
        new_doc.doctype = 3
        new_doc.anchor = old_doc.anchor
        new_doc.user = user
        new_doc.cc_ref = ref
        new_doc.save()
        
        new_doc.set_default_locator()
        new_doc.docs_prev.add(old_doc)
        new_doc.save()
        
        new_tx.post_balance(user, "On-site payment (cash or check) received", money_target)

        return new_doc
    
    def get_items(self):
        return self.txn.lineitem_set.all()
    
    def cost(self, mask_receivable=False):
        """ Get the cost of line items on a document.
        If mask_receivable is set to True, line items posting to Accounts Receivable
        (which represent anticipated, not real, funds) will be ignored in the
        calculation. """
        receivable_parent = DataTree.get_by_uri('Q/Accounts/Receivable/', create=True)
        try:
            if not mask_receivable:
                return self.txn.get_balance()
            else:
                bal = 0
                for li in self.get_items():
                    if li.anchor not in receivable_parent:
                        bal -= li.amount
                return bal
        except EmptyTransactionException:
            return 0

    def getDoctypeStr(self):
        doctypes = dict(self.TYPE_CHOICES)
        return doctypes[self.doctype]
    
    class Admin:
        pass
