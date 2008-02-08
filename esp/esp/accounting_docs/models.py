
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
from esp.datatree.models import DataTree
from esp.db.fields import AjaxForeignKey
from esp.accounting_core.models import LineItemType, Balance, Transaction, LineItem
from esp.accounting_docs.checksum import Checksum
from esp.users.models import ESPUser
from datetime import datetime

from esp.middleware import ESPError_Log
from esp.accounting_core.models import Transaction

class MultipleDocumentError(ESPError_Log):
    pass

class PurchaseOrder(models.Model):
    """ A purchase order available for invoicing in a given accounting ledger """
    anchor = AjaxForeignKey(DataTree)
    address = models.TextField()
    fax = models.CharField(blank=True, maxlength=16)
    phone = models.CharField(blank=True, maxlength=16)
    email = models.EmailField(blank=True)
    reference = models.TextField()
    rules = models.TextField()
    notes = models.TextField()

    def __unicode__(self):
        return u'PurchaseOrder account %u (ref: %s)' % (self.id, self.reference)
    
    class Admin:
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
    user = AjaxForeignKey(User, blank=True, null=True)
    txn = models.ForeignKey(Transaction)
    doctype = models.IntegerField(choices=TYPE_CHOICES)

    # Document workflow (creates next_set and prev_set)
    docs_next = models.ManyToManyField('self', symmetrical=False, related_name='docs_prev')

    # Document references
    locator = models.CharField(maxlength=16, unique=True)
    po = models.ForeignKey(PurchaseOrder, null=True)
    cc_ref = models.TextField(blank=True,default='')

    # Tools
    _checksum = Checksum(rotors=2, base_length=8)
    
    
    #   This is new and untested code, fortunately we don't use it yet.
    #   Michael P, 2/5/2008
    
    def set_default_locator(self):
        self.locator = Document._checksum.calculate(str(self.id))

    def get_locator(self):
        if self.locator == None or self.locator == '':
            self.set_default_locator()

        return self.locator

    @staticmethod
    def get_invoice(user, anchor, li_types=[], dont_duplicate=False, finaid=None):
        """ Create an "empty shopping cart" for a particular user in a particular
        anchor (i.e. program). """
        
        if finaid is None:
            finaid = ESPUser(user).hasFinancialAid(anchor)
        
        qs = Document.objects.filter(user=user, anchor=anchor, txn__complete=False)
        
        if qs.count() > 1:
            raise MultipleDocumentError(False), 'Found multiple uncompleted transactions for this user and anchor.'
        elif qs.count() == 1:
            return qs[0]
        else:
            new_tx = Transaction.begin(anchor, 'User payments for %s: %s' % (anchor.parent.friendly_name, anchor.friendly_name))
            new_tx.save()
            for lit in li_types:
                if not dont_duplicate or new_tx.lineitem_set.filter(li_type=lit).count() == 0:
                    new_tx.add_item(user, lit, finaid)
                
            new_doc = Document()
            new_doc.txn = new_tx
            new_doc.anchor = anchor
            new_doc.doctype = 2
            new_doc.user = user
            new_doc.locator = 'N/A'
            new_doc.save()
            
            new_doc.set_default_locator()
            new_doc.save()
            
            return new_doc
    
    @staticmethod
    def get_by_locator(loc):
        return Document.objects.filter(locator=loc)
    
    @staticmethod
    def receive_creditcard(user, loc, amt, cc_id):
        """ Call this function when a successful credit card payment is received. """
        old_doc = Document.get_by_locator(loc)

        new_tx = Transaction.begin(cart.anchor, 'Credit card payment')
        li_type = LineItemType.objects.get_or_create(text='Credit Card Payment',anchor=nodes['cc-pending'])
        new_tx.add_item(user, li_type, amount=amt)
        
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
        
        return new_doc
    
    def get_items(self):
        return self.txn.lineitem_set.all()
    
    def cost(self):
        return -self.txn.get_balance()
    
    class Admin:
        pass
