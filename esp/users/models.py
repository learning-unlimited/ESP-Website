from django.db import models
from django.contrib.auth.models import User
from esp.workflow.models import Controller
from peak.api import security, binding


# Create your models here.

class ESPUser(models.Model):
    """ Create a user of the ESP Website """
    user = models.OneToOneKey(User) # Django user that we're connected to

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(ESPUser) # User to give this permission
    permission = models.ForeignKey(Controller) # Controller to grant access to

class RecursiveTreeCheck(security.Context):
    # [ security.hasPermission.when("user!=God") ] # What do I do for "Always"?  Do we want "Always"?
    def espUserHasPerms(self, user, perm, subject):
        for bit in user.userbits():
            if bit.permission.is_child_of(perm):
                return True

        return security.Denial("User " + str(user) + " doesn't have the permission " + str(perm))
    
