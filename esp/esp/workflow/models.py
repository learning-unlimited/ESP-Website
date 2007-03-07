
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
from esp.datatree.models import DataTree

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

        tree = models.ForeignKey(DataTree) # Tree node that this workflow belongs to
        controller = models.SlugField()

        class Admin:
            pass

class ControllerDB(models.Model):
    """ A registry of the names of all known subclasses of Controller.  Used by the auth system as unique identifiers of these controllers. """
    contr_name = models.SlugField(blank=False)
    # Name of the relevant controller class (value of its __name__ field).  Note that this forces Controller classes to have universally unique names.

    class Admin:
        pass
    

