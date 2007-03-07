
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
from django.db import models
from django.contrib.auth.models import User
from esp.datatree.models import DataTree
from datetime import datetime

class LineItem(models.Model):
	value = models.FloatField(max_digits = 10, decimal_places = 2)
	label = models.TextField()
	
	def __str__(self):
		return str(self.label) + str(self.value)
		
	class Admin:
		pass

class PaymentType(models.Model):
    """ A list of payment methods: Check, Credit Card, etc. """
    description = models.TextField() # Description, ie. "Check", "Credit Card", etc.

    def __str__(self):
        return str(self.description)

    class Admin:
        pass

    
class Transaction(models.Model):
    """ A monetary transaction """
    anchor = models.ForeignKey(DataTree) # Region of ESP that receives the transaction
    payer = models.ForeignKey(User, related_name="payer") # Source of the money
    fbo = models.ForeignKey(User, related_name="fbo") # Payment is for the benefit of this user
    amount = models.FloatField(max_digits=9, decimal_places=2) # Amount to be payed
    line_item = models.TextField() # Description of the reason for this payment
    payment_type = models.ForeignKey(PaymentType) # Type of payment; ie. credit card, check, cash, etc.

    transaction_id = models.CharField(maxlength=128) # Identifier of the transaction; check number, or that sort of information.  Should probably not contain credit card numbers; possibly a hash of the last four digits?, or not at all?

    executed = models.BooleanField() # Has this transaction taken place?
    
    last_ts = models.DateTimeField(default=datetime.now())
    update_ts = models.DateTimeField(default=datetime.now())

    def pretty_amount(self):
	if self.amount is None:
		return 'No transaction took place.'
	else:
		return '$%02.2f' % self.amount

    def __str__(self):
        return str(self.line_item) + ': $' + str(self.amount) + ' <' + str(self.fbo) + '>'

    class Admin:
        pass
    

