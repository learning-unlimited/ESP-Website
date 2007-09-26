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

""" Models for Resources application """

from esp.cal.models import Event
from esp.users.models import User
from esp.db.fields import AjaxForeignKey

from django.db import models
import pickle

########################################
#   New resource stuff (Michael P)
########################################

"""
Models (see more below):
    -   Resource types include classrooms, teacher availability, various equipment and furnishings.
    -   Resources are the individual "things"; the group id determines which are bunched together (such as a classroom and its big chalkboards).
    -   Resource requests ask for a particular filter on resources (including, by default, just their types).
    -   Resource assignments bind resources to events.
        
Procedures:
    -   Teacher availability module creates resources for each time slot a teacher is available for.
    -   Program resources module lets admin put in classrooms and equipment for the appropriate times.
"""

class ResourceType(models.Model):
    """ A type of resource (e.g.: Projector, Classroom, Box of Chalk) """
    
    name = models.CharField(maxlength=40)                          #   Brief name
    description = models.TextField()                                #   What is this resource?
    consumable  = models.BooleanField(default = False)              #   Is this consumable?  (Not usable yet. -Michael P)
    priority_default = models.IntegerField(blank=True, default=-1)  #   How important is this compared to other types?
    attributes_pickled  = models.TextField(blank=True)                        

    def _get_attributes(self):
        if hasattr(self, '_attributes_cached'):
            return self._attributes_cached
        
        if self.attributes_pickled:
            try:
                self._attributes_cached = pickle.loads(self.attributes_pickled)
            except:
                self._attributes_cached = None
        else:
            self._attributes_cached = None

        return self._attributes_cached

    def _set_attributes(self, val):
        self._attributes_cached = val

    attributes = property(_get_attributes, _set_attributes)

    """ Don't know why this doesn't work. Hope to fix soon. -Michael P
    def save(self, *args, **kwargs):
        if hasattr(self, '_attributes_cached'):
            self.attributes_pickled = pickle.dumps(self._attributes_cached)
        super(ResourceType, self).save(*args, **kwargs)
    """
    @staticmethod
    def get_or_create(label):
        current_type = ResourceType.objects.filter(name__icontains=label)
        if len(current_type) != 0:
            return current_type[0]
        else:
            nt = ResourceType()
            nt.name = label
            nt.description = ''
            nt.save()
            return nt

    def __str__(self):
        return 'Resource Type "%s", priority=%d' % (self.name, self.priority_default)
    
    class Admin:
        pass

class ResourceRequest(models.Model):
    """ A request for a particular type of resource associated with a particular class. """
    from esp.program.models.class_ import Class
    
    target = models.ForeignKey(Class)
    res_type = models.ForeignKey(ResourceType)
    
    def __str__(self):
        return 'Resource request of %s for %s' % (str(self.res_type), self.target.emailcode())

    class Admin:
        pass
    
class Resource(models.Model):
    """ An individual resource, such as a class room or piece of equipment.  Categorize by
    res_type, attach to a user if necessary. """
    
    name = models.CharField(maxlength=80)
    res_type = models.ForeignKey(ResourceType)
    num_students = models.IntegerField(blank=True, default=-1)
    group_id = models.IntegerField(default=-1)
    user = AjaxForeignKey(User, null=True, blank=True)
    event = models.ForeignKey(Event)
    
    def __init__(self, *args, **kwargs):
        #   Find highest group id so far and make this one higher by default.
        #   Often the group id will be manually set by other code immediately after instantiation.
        
        vals = Resource.objects.all().order_by('-group_id').values('group_id')
        max_id = 0
        if len(vals) > 0:
            max_id = vals[0]['group_id']
            
        self.group_id = max_id + 1
        
        super(Resource, self).__init__(*args, **kwargs)
    
    def __str__(self):
        if self.user is not None:
            return 'Resource for %s: %s (%s)' % (str(self.user), self.name, str(self.res_type))
        else:
            if self.num_students != -1:
                return 'Resource for %d students: %s (%s)' % (self.num_students, self.name, str(self.res_type))
            else:
                return 'Resource: %s (%s)' % (self.name, str(self.res_type))
    
    class Admin:
        pass
    
class ResourceAssignment(models.Model):
    """ The binding of a resource to the class that it belongs to. """
    from esp.program.models.class_ import Class
    
    resource = models.ForeignKey(Resource)     #   Note: this really points to a bunch of Resources.
                                               #   See resources() below.
                                               
    target = models.ForeignKey(Class)          #   Change to Event later?
    
    def __str__(self):
        return 'Resource assignment for %s' % str(self.target)
    
    def resources(self):
        return Resource.objects.filter(group_id=self.resource.group_id)
    
    class Admin:
        pass
    
    
