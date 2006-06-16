from django.db import models
from django.contrib.auth.models import User
from esp.workflow.models import Controller

# Create your models here.

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(User) # User to give this permission
    permission = models.ForeignKey(Controller) # Controller to grant access to

