
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
from datatree.models import DataTree
from db.fields import AjaxForeignKey
from accounting_core import *
from checksum import Checksum

class PurchaseOrder(models.Model):
        """ A purchase order available for invoicing in a given accounting ledger """
        anchor = AjaxForeignKey(DataTree)
        address = models.TextField()
        fax = models.CharField(blank=True, max_length=16)
        phone = models.CharField(blank=True, max_length=16)
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
        txn = models.ForeignKey(Transaction)
        doctype = models.IntegerField(choices=TYPE_CHOICES)

        # Document workflow (creates next_set and prev_set)
        docs_next = models.ManyToManyField('self', symmetrical=False, related_name='docs_prev')

        # Document references
        locator = models.CharField(max_length=16, unique=True)
        po = models.ForeignKey(PurchaseOrder, null=True)
        cc_ref = models.TextField(blank=True,default='')

        # Tools
        _checksum = Checksum(rotors=2, base_length=8)
