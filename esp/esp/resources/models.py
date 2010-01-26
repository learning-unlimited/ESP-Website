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
from esp.middleware import ESPError_Log
from esp.cache import cache_function

from django.db import models
from django.db.models.query import Q
from django.core.cache import cache

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

GLOBAL_RESOURCE_CACHE_KEY="RESOURCE__GLOBAL_KEY"

DISTANCE_FUNC_REGISTRY = {}

def global_resource_rev():
    retVal = cache.get(GLOBAL_RESOURCE_CACHE_KEY)
    if retVal:
        return retVal
    else:
        return increment_global_resource_rev()

def increment_global_resource_rev():
    import random
    val = random.randint(1,2**30)
    cache.set(GLOBAL_RESOURCE_CACHE_KEY, val, timeout=86400)
    return val

class ResourceType(models.Model):
    """ A type of resource (e.g.: Projector, Classroom, Box of Chalk) """
    from esp.survey.models import ListField

    name = models.CharField(max_length=40)                          #   Brief name
    description = models.TextField()                                #   What is this resource?
    consumable  = models.BooleanField(default = False)              #   Is this consumable?  (Not usable yet. -Michael P)
    priority_default = models.IntegerField(default=-1)  #   How important is this compared to other types?
    attributes_pickled  = models.TextField(default="Don't care", blank=True, help_text="A pipe (|) delimited list of possible attribute values.")       
    #   As of now we have a list of string choices for the value of a resource.  But in the future
    #   it could be extended.
    choices = ListField('attributes_pickled')
    program = models.ForeignKey('program.Program', null=True, blank=True)                 #   If null, this resource type is global.  Otherwise it's specific to one program.
    distancefunc = models.TextField(
        blank=True,
        null=True,
        help_text="Enter python code that assumes <tt>r1</tt> and <tt>r2</tt> are resources with this type.",
        )               #   Defines a way to compare this resource type with others.

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

    def save(self, *args, **kwargs):
        if hasattr(self, '_attributes_cached'):
            self.attributes_pickled = pickle.dumps(self._attributes_cached)
        super(ResourceType, self).save(*args, **kwargs)

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
        
    @staticmethod
    def global_types():
        return ResourceType.objects.filter(program__isnull=True)

    def __unicode__(self):
        return 'Resource Type "%s", priority=%d' % (self.name, self.priority_default)
    
    class Admin:
        pass

class ResourceRequest(models.Model):
    """ A request for a particular type of resource associated with a particular clas section. """
    
    target = models.ForeignKey('program.ClassSection', null=True)
    target_subj = models.ForeignKey('program.ClassSubject', null=True)
    res_type = models.ForeignKey(ResourceType)
    desired_value = models.TextField()
    
    def __unicode__(self):
        return 'Resource request of %s for %s: %s' % (unicode(self.res_type), self.target.emailcode(), self.desired_value)

    class Admin:
        pass
    
class Resource(models.Model):
    """ An individual resource, such as a class room or piece of equipment.  Categorize by
    res_type, attach to a user if necessary. """
    
    name = models.CharField(max_length=80)
    res_type = models.ForeignKey(ResourceType)
    num_students = models.IntegerField(blank=True, default=-1)
    group_id = models.IntegerField(default=-1) # Default value of -1 means ungrouped, or at least so I'm assuming for now in grouped_resources(). -ageng 2008-05-13
    is_unique = models.BooleanField(default=False)
    user = AjaxForeignKey(User, null=True, blank=True)
    event = models.ForeignKey(Event)
    
    def __unicode__(self):
        if self.user is not None:
            return 'For %s: %s (%s)' % (unicode(self.user), self.name, unicode(self.res_type))
        else:
            if self.num_students != -1:
                return 'For %d students: %s (%s)' % (self.num_students, self.name, unicode(self.res_type))
            else:
                return '%s (%s)' % (self.name, unicode(self.res_type))
    
    def save(self, *args, **kwargs):
        if self.group_id == -1:
            #   Give this a new group id.
            vals = Resource.objects.all().order_by('-group_id').values_list('group_id', flat=True)
            max_id = 0
            if len(vals) > 0:
                max_id = vals[0]
                
            self.group_id = max_id + 1
            self.is_unique = True
        else:
            self.is_unique = False

        cache_key_QObjects = "RESOURCE__%s__IS_AVAILABLE__QObjects" % self.id
        cache_key = "RESOURCE__%s__IS_AVAILABLE" % self.id
        
        super(Resource, self).save(*args, **kwargs)

        cache.delete(cache_key_QObjects)
        cache.delete(cache_key)

        increment_global_resource_rev()

    def distance(self, other):
        """
        Using the custom distance function defined in the ResourceType,
        compute the distance between this resource and another.
        Bear in mind that this is cached using a python global registry.
        """
        if self.res_type_id != other.res_type_id:
            raise ValueError("Both resources must be of the same type to compare!")

        if self.res_type_id in DISTANCE_FUNC_REGISTRY:
            return DISTANCE_FUNC_REGISTRY[self.res_type_id](self, other)

        distancefunc = self.res_type.distancefunc

        if distancefunc and distancefunc.strip():
            funcstr = distancefunc.strip().replace('\r\n', '\n')
        else:
            funcstr = "return 0"
        funcstr = """def _cmpfunc(r1, r2):\n%s""" % (
            '\n'.join('    %s' % l for l in funcstr.split('\n'))
            )
        exec funcstr
        DISTANCE_FUNC_REGISTRY[self.res_type_id] = _cmpfunc
        return _cmpfunc(self, other)

    __sub__ = distance


    def identical_resources(self):
        res_list = Resource.objects.filter(name=self.name)
        return res_list
    
    def satisfies_requests(self, req_class):
        #   Returns a list of 2 items.  The first element is boolean and the second element is a list of the unsatisfied requests.
        #   If there are no unsatisfied requests but the room isn't big enough, the first element will be false.
        cache_key = "RESOURCES__SATISFIES_REQUESTS__%s__%s" % (self.id, global_resource_rev())

        result = cache.get(cache_key)
        if not result:
            result = [True, []]
            request_list = req_class.getResourceRequests()
            furnishings = self.associated_resources()
            id_list = []

            for req in request_list:
                if furnishings.filter(res_type=req.res_type).count() < 1:
                    result[0] = False
                    id_list.append(req.id)
            
            result[1] = ResourceRequest.objects.filter(id__in=id_list)

            cache.set(cache_key, result, timeout=86400)
            
        if self.num_students < req_class.num_students():
            result[0] = False
        
        return result
    
    def grouped_resources(self):
        if self.group_id == -1:
            return Resource.objects.filter(id=self.id)
        return Resource.objects.filter(group_id=self.group_id)
    
    def associated_resources(self):
        return self.grouped_resources().exclude(id=self.id).exclude(res_type__name='Classroom')
    
    #   Modified to handle assigning rooms to both classes and their individual sections.
    #   Resource assignments are always handled at the section level now. 
    #   The assign_to_class function is copied for backwards compatibility.
    
    def assign_to_subject(self, new_class, check_constraint=True):
        for sec in new_class.sections.all():
            self.assign_to_section(sec, check_constraint)
        
    def assign_to_section(self, section, check_constraint=True, override=False):
        if override:
            self.clear_assignments()
        if self.is_available():
            new_ra = ResourceAssignment()
            new_ra.resource = self
            new_ra.target = section
            new_ra.save()
        else:
            raise ESPError_Log, 'Attempted to assign class section %d to conflicted resource; and constraint check was on.' % section.id
        
    assign_to_class = assign_to_section
        
    def clear_assignments(self, program=None):
        if program is not None:
            self.clear_schedule_cache(program)
            
        self.assignments().delete()

    def assignments(self):
        cache_key = "RESOURCE__ASSIGNMENTS__%s__%s" % (self.id, global_resource_rev())
        retVal = cache.get(cache_key)
        if retVal:
            return retVal
        
        retVal = ResourceAssignment.objects.filter(resource__in=self.grouped_resources())
        cache.set(cache_key, retVal, timeout=86400)
        return retVal
    
    def cache_key(self, program):
        #   Let's make this key acceptable to memcached...
        chars_to_avoid = '~!@#$%^&*(){}_ :;,"\\?<>'
        clean_name = ''.join(c for c in self.name if c not in chars_to_avoid)
        return 'resource__schedule_sequence:%s,%d' % (clean_name, program.id)
    
    def clear_schedule_cache(self, program):
        from django.core.cache import cache
        from esp.program.templatetags.scheduling import schedule_key_func
        cache.delete(self.cache_key(program))
        other_key = schedule_key_func(self, program)
        cache.delete(other_key)
    
    def schedule_sequence(self, program):
        """ Returns a list of strings, which are the status of the room (and its identical
        companions) at each time block belonging to the program. """
        from django.core.cache import cache
        
        result = cache.get(self.cache_key(program))
        if result is not None:
            return result
        
        sequence = []
        event_list = list(program.getTimeSlots())
        room_list = self.identical_resources().filter(event__in=event_list)
        for timeslot in event_list:
            single_room = room_list.filter(event=timeslot)
            if single_room.count() == 1:
                room = single_room[0]
                asl = list(room.assignments())
            
                if len(asl) == 0:
                    sequence.append('Empty')
                elif len(asl) == 1:
                    sequence.append(asl[0].getTargetOrSubject().emailcode())
                else:
                    init_str = 'Conflict: '
                    for ra in asl:
                        init_str += ra.getTargetOrSubject().emailcode() + ' '
                    sequence.append(init_str)
            else:
                sequence.append('N/A')
            
        cache.set(self.cache_key(program), sequence)
        return sequence
    
    def is_conflicted(self):
        return (self.assignments().count() > 1)
    
    def available_any_time(self, anchor=None):
        return (len(self.available_times(anchor)) > 0)
    
    def available_times(self, anchor=None):
        if anchor:
            event_list = filter(lambda x: self.is_available(timeslot=x), list(self.matching_times().filter(anchor=anchor)))
        else:
            event_list = filter(lambda x: self.is_available(timeslot=x), list(self.matching_times()))
        return '<br /> '.join([unicode(e) for e in Event.collapse(event_list)])
    
    def matching_times(self):
        #   Find all times for which a resource of the same name is available.
        event_list = self.identical_resources().values_list('event', flat=True)
        return Event.objects.filter(id__in=event_list).order_by('start')
    
    def is_independent(self):
        if self.is_unique:
            return True
        else:
            return False
        
    @cache_function
    def is_available(self, QObjects=False, timeslot=None):
        if timeslot is None:
            test_resource = self
        else:
            test_resource = self.identical_resources().filter(event=timeslot)[0]
        
        if QObjects:
            return ~Q(test_resource.is_taken(True))
        else:
            return not test_resource.is_taken(False)
    is_available.depend_on_row(lambda:ResourceAssignment, lambda instance: {'self': instance.resource})
    is_available.depend_on_row(lambda:Event, lambda instance: {'timeslot': instance})
    
    def is_taken(self, QObjects=False):
        if QObjects:
            return Q(resource=self)
        else:
            collision = ResourceAssignment.objects.filter(resource=self)
            return (collision.count() > 0)
    
    class Admin:
        pass
    
class ResourceAssignment(models.Model):
    """ The binding of a resource to the class that it belongs to. """
    
    resource = models.ForeignKey(Resource)     #   Note: this really points to a bunch of Resources.
                                               #   See resources() below.
                                               
    target = models.ForeignKey('program.ClassSection', null=True)
    target_subj = models.ForeignKey('program.ClassSubject', null=True)

    def save(self, *args, **kwargs):
        cache_key_QObjects = "RESOURCE__%s__IS_AVAILABLE__QObjects" % self.resource.id
        cache_key = "RESOURCE__%s__IS_AVAILABLE" % self.resource.id
        
        super(ResourceAssignment, self).save(*args, **kwargs)

        cache.delete(cache_key_QObjects)
        cache.delete(cache_key)

        increment_global_resource_rev()
        
    
    def __unicode__(self):
        return 'Resource assignment for %s' % unicode(self.getTargetOrSubject())
    
    def getTargetOrSubject(self):
        """ Returns the most finely specified target. (target if it's set, target_subj otherwise) """
        if self.target is not None:
            return self.target
        return self.target_subj
    
    def resources(self):
        return Resource.objects.filter(group_id=self.resource.group_id)
    
    class Admin:
        pass
    
    
def install():
    #   Create default resource types.
    ResourceType.objects.get_or_create(name='Classroom',description='Type of classroom',attributes_pickled='Lecture|Discussion|Outdoor|Lab|Open space')
    ResourceType.objects.get_or_create(name='A/V',description='A/V equipment',attributes_pickled='LCD projector|Overhead projector|Amplified speaker|VCR|DVD player')
    ResourceType.objects.get_or_create(name='Computer[s]',description='Computer[s]',attributes_pickled='ESP laptop|Athena workstation|Macs for students|Windows PCs for students|Linux PCs for students')
    ResourceType.objects.get_or_create(name='Seating',description='Seating arrangement',attributes_pickled="Don't care|Fixed seats|Movable desks")
    ResourceType.objects.get_or_create(name='Light control',description='Light control',attributes_pickled="Don't care|Darkenable")
    
