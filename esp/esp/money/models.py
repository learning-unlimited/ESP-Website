
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
from esp.db.fields import AjaxForeignKey
from esp.program.models import FinancialAidRequest
from esp.users.models import ESPUser

def RegisterLineItem(espuser, lineitemtype):
	"""  
	Register (create) a Line Item for the given user/type/anchor triple.
	Do nothing if this LineItem already exists once.
	Fail badly if it already exists more than once (this should not be permitted).
	Return the tuple (newLineItem, wasLineItemCreated?)
	"""
	return LineItem.objects.get_or_create(type=lineitemtype, user=espuser)


def UnRegisterLineItem(espuser, lineitemtype):
	"""
	Remove all Line Items matching the user/type/anchor triple given.
	DOES NOT REMOVE Line Items that have already been paid for.
	"""
	LineItem.objects.filter(type=lineitemtype, user=espuser, transaction__isnull=True).delete()


def PayForLineItems(espuser, anchor, transaction):
	"""
	Register payment for all Line Items at a particular anchor point
	Return True iff any Line Items are updated
	"""

	ExistsAlready = False

	for l in LineItem.objects.filter(user=espuser, type__anchor=anchor):
		l.transaction = transaction;
		l.save()
		ExistsAlready = True

	return ExistsAlready


class PaymentType(models.Model):
    """ A list of payment methods: Check, Credit Card, etc. """
    description = models.TextField() # Description, ie. "Check", "Credit Card", etc.

    def __str__(self):
        return str(self.description)

    class Admin:
        pass

    
class Transaction(models.Model):
    """ A monetary transaction """
    anchor = AjaxForeignKey(DataTree) # Region of ESP that receives the transaction
    payer = AjaxForeignKey(User, related_name="payer") # Source of the money
    fbo = AjaxForeignKey(User, related_name="fbo") # Payment is for the benefit of this user
    amount = models.DecimalField(max_digits=9, decimal_places=2) # Amount to be payed
    line_item = models.TextField() # Description of the reason for this payment
    payment_type = models.ForeignKey(PaymentType) # Type of payment; ie. credit card, check, cash, etc.

    transaction_id = models.CharField(max_length=128) # Identifier of the transaction; check number, or that sort of information.  Should probably not contain credit card numbers; possibly a hash of the last four digits?, or not at all?

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
    

class LineItemType(models.Model):
	value = models.DecimalField(max_digits = 10, decimal_places = 2)
	financial_aid_value = models.DecimalField(max_digits=10, decimal_places=2)
        onsite_value = models.DecimalField(max_digits=10, decimal_places=2)
	label = models.TextField()
	anchor = AjaxForeignKey(DataTree)
	optional = models.BooleanField(default=True)
	show_on_schedule = models.BooleanField(default=False, null=True)

	@classmethod
	def forAnchor(cls, anchor):
		return cls.objects.filter(anchor=anchor)

	def __str__(self):
		return str(self.label) + " : " + str(self.value) + "/" + str(self.financial_aid_value) + " (for %s)" % self.anchor

	class Admin:
		pass

class LineItem(models.Model):
	type = models.ForeignKey(LineItemType)
	user = AjaxForeignKey(User)
	transaction = models.ForeignKey(Transaction, null=True)	

	def hasPaid(self):
		return (self.transaction != None)

	@staticmethod
	def student_has_financial_aid(espuser, anchor):
		""" Has the student in question applied for and received financial aid? """
		return ( FinancialAidRequest.objects.filter(user=espuser, program__anchor=anchor, approved__isnull=False).count() > 0 )

	def has_financial_aid(self):
		return ( FinancialAidRequest.objects.filter(user=self.user, program__anchor=self.type.anchor, approved__isnull=False).count() > 0 )

	@classmethod
	def purchased(cls, anchor, espuser, filter_already_paid=True):
		if filter_already_paid:
			return cls.objects.filter(user=espuser, type__anchor=anchor).exclude(transaction__isnull=False)
		else:
			return cls.objects.filter(user=espuser, type__anchor=anchor)

	@classmethod
	def purchasedTypes(cls, anchor, espuser, filter_already_paid=True):
		if filter_already_paid:
			return LineItemType.objects.filter(lineitem__user=espuser, anchor=anchor).exclude(lineitem__transaction__isnull=False)
		else:
			return LineItemType.objects.filter(lineitem__user=espuser, anchor=anchor)

	@classmethod
	def purchasedTotalCost(cls, anchor, espuser, filter_already_paid=True):
		my_costs = cls.purchased(anchor, espuser, filter_already_paid)
		my_costs_sum=0
		if cls.student_has_financial_aid(espuser, anchor):
			for i in my_costs:
				my_costs_sum += i.type.financial_aid_value
		else:
			if hasattr(espuser, 'other_user') and espuser.other_user:
				for i in my_costs:
					my_costs_sum += i.type.onsite_value
			else:			
                        	for i in my_costs:
					my_costs_sum += i.type.value

		return my_costs_sum


	def __str__(self):
		return "%s : %s" % (str(self.user), str(self.type))
	
	class Admin:
		pass

