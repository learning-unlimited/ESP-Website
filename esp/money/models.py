from django.db import models
from django.contrib.auth.models import User


class PaymentType(models.Model):
    """ A list of payment methods: Check, Credit Card, etc. """
    description = models.TextField() # Description, ie. "Check", "Credit Card", etc.

class Transaction(models.Model):
    """ A monetary transaction """
    anchor = models.ForeignKey(DataTree) # Region of ESP that receives the transaction
    payer = models.ForeignKey(User) # Source of the money
    fbo = models.ForeignKey(User) # Payment is for the benefit of this user
    amount = models.FloatField(max_digits=9, decimal_places=2) # Amount to be payed
    line_item = models.TextField() # Description of the reason for this payment
    payment_type = models.ForeignKey(PaymentType) # Type of payment; ie. credit card, check, cash, etc.

    
    
