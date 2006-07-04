from django.db import models
from django.contrib.auth.models import User
from esp.datatree.models import DataTree

# Create your models here.
    
class Subscription(models.Model):
    """ Allows a user to 'subscribe', to watch for e-mail notices from, a particular category; the EmailController workflow handles the logic to check for this """
    user = models.ForeignKey(User)
    category = models.ForeignKey(DataTree)

    def __str__(self):
        return str(self.user.username) + ': ' + str(self.category)

    class Admin:
        pass
