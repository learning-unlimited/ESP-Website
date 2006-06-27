from django.db import models
from django.contrib.auth.models import User
from esp.watchlists.models import Datatree
from peak.api import security, binding
from esp.workflows.models import Controller

# Create your models here.

class ESPUser(models.Model):
    """ Create a user of the ESP Website """
    user = models.OneToOneKey(User) # Django user that we're connected to
#    bits = models.ManyToMany(Datatree)

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(ESPUser) # User to give this permission
    permission = models.ForeignKey(Datatree) # Controller to grant access to
    subject = models.ForeignKey(Datatree) # Do we want to use Subjects?

class RecursiveTreeCheck(security.Context):
    """ If a permission is heirarchical (parents have all the bits of their children), check this user against it """
    [ security.hasPermission.when("perm.mode_data.heirarchical_top_down==True") ]
    def espUserHasPerms(self, user, perm, subject):
        for bit in user.userbit_all():
            for perm in bit.permission:
                if perm.permission.is_descendant(perm) & perm.subject.is_antecedent(subject):
                    return True

        return security.Denial("User " + str(user) + " doesn't have the permission " + str(perm))

def enforce_bits(controller_class, user):
    def call(proc, *args):
        """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a user; returns a function that runs the 'run' function and returns 'true' if the user can access this Controller class, and returns 'false' otherwise. """
        proc(args)
        return True

    if UserBit.objects.filter(permission__controller=controller_class.__name__).filter(user_pk=user.id).count() != 0:
        return decorator(call)
    else:
        return lambda : False
