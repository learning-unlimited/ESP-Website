from django.db import models
from esp.watchlists.models import Datatree, DatatreeNodeData
from esp.users.models import UserBit

# Create your models here.

# Argh: No virtual classes in Python?
class Controller:
    def sync_to_db(self):
        """ Record our name to the database table of Controllers.  Don't record a duplicate. """
        if Controller.objects.filter(controller=self.__name__).count() == 0:
            c = Controller()
            c.controller = self.__name__
            c.save()

    """ A generic virtual superclass, that all Controllers inherit from """
    def run(self, data, user):
        """ Do some action based on a given chunk of data """
        pass


class WorkflowDescriptor(models.Model):
        """ Provides an identifier for a workflow within the database;
        workflows don't have an inherent database presence.

        Links each workflow to a node in the permissions tree. """

        tree = models.ForeignKey(DatatreeNodeData) # Tree node that this workflow belongs to
        controller = models.ForeignKey(Controller)

        class Admin:
            pass

class Controller(models.Model):
    """ A registry of the names of all known subclasses of Controller.  Used by the auth system as unique identifiers of these controllers. """
        controller = models.TextField(blank=False) # Name of the relevant controller class (value of its __name__ field).  Note that this forces Controller classes to have universally unique names.

def enforce_bits(controller_class, user):
    def call(proc, *args):
        """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a user; returns a function that runs the 'run' function and returns 'true' if the user can access this Controller class, and returns 'false' otherwise. """
        proc(args)
        return True

    if UserBit.objects.filter(permission__controller=controller_class.__name__).filter(user_pk=user.id).count() != 0:
        return decorator(call)
    else:
        return lambda : False
