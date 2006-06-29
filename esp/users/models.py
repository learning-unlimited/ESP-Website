from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.watchlists.models import Datatree
from peak.api import security, binding
from esp.workflow.models import Controller

# Create your models here.

class ESPUser(models.Model):
    """ Create a user of the ESP Website """
    user = models.OneToOneField(User) # Django user that we're connected to
#    bits = models.ManyToMany(Datatree)

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(ESPUser) # User to give this permission
    permission = models.ForeignKey(Datatree) # Controller to grant access to
    subject = models.ForeignKey(Datatree) # Do we want to use Subjects?

#class RecursiveTreeCheck:
#    """ If a permission is heirarchical (parents have all the bits of their children), check this user against it """
#    [ security.hasPermission.when("perm.mode_data.heirarchical_top_down==True") ]
def espUserHasPerms(user, perm, subject):
    """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
    if user != None:
        for bit in user.userbit_all():
            if bit.permission.permission.is_descendant(perm) & bit.permission.subject.is_antecedent(subject):
                return True

    # This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
    for bit in UserBit.objects.filter(user_pk=AnonymousUser().id):
        if bit.permission.permission.is_descendant(perm) & bit.permission.subject.is_antecedent(subject):
            return True

    # security.Denial() evaluates to False as necessary; it also makes peak happy, though we're not using peak any more
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
