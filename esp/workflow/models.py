from django.db import models
from esp.watchlists.models import Datatree, DatatreeNodeData

# Create your models here.

# Argh: No virtual classes in Python?
class Controller(object):
    def sync_to_db():
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
        controller = models.SlugField()

        class Admin:
            pass

class ControllerDB(models.Model):
    """ A registry of the names of all known subclasses of Controller.  Used by the auth system as unique identifiers of these controllers. """
    contr_name = models.SlugField(blank=False)
    # Name of the relevant controller class (value of its __name__ field).  Note that this forces Controller classes to have universally unique names.

    class Admin:
        pass
    
