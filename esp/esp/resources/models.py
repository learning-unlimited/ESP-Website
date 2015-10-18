__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

""" Models for Resources application """

from esp.cal.models import Event
from esp.users.models import User, ESPUser
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError
from esp.cache import cache_function
from esp.tagdict.models          import Tag

from django.db import models
from django.db.models.query import Q
from django.core.cache import cache

import pickle
import warnings


#####################
# New resource stuff
#####################

class Location(models.Model):
    """A place a class might be held, such as a classroom."""
    name = models.CharField(
        max_length=100, help_text='The name or room number')
    capacity = models.IntegerField(
        help_text='The number of students the location can accommodate')
    admin_notes = models.TextField(blank=True,
        help_text='Notes on this classroom visible only to admins')
    teacher_notes = models.TextField(blank=True,
        help_text="Notes on this classroom that will appear on teachers'"
        "schedules.")
    student_notes = models.TextField(blank=True,
        help_text="Notes on this classroom that will appear on students'"
        "schedules.")

    def __unicode__(self):
        return '%s (capacity %s)' % (self.name, self.capacity)

    def furnishings(self, program):
        # TODO(benkraft): one day this will not need to be terrible
        return ResourceType.objects.filter(
            program=program,
            resource__res_group__location=self).distinct()
    
    # TODO(benkraft): change this to be the actually correct thing once we kill
    # resource groups fully.  Also, at that point, make it into something that
    # can be prefetched.
    def associated_resources(self):
        return Resource.objects.filter(res_group__location=self)

    def merge_with(self, other):
        """Merge this location with another.

        This can be used when there are two locations that represent the same
        room, to deduplicate.  The other location will be deleted, and all
        related objects will be pointed at this one.
        """
        # prevent the circular import
        from esp.program.models import ClassSection
        # running this with self == other would basically just delete the
        # Location, so let's not do that.
        assert self.id != other.id
        ResourceGroup.objects.filter(location=other).update(location=self)
        for sec in ClassSection.objects.filter(locations=other):
            sec.locations.add(self)
            sec.locations.remove(other)
        for event in Event.objects.filter(available_locations=other):
            event.available_locations.add(self)
            event.available_locations.remove(other)
        other.delete()




#####################################################
#   Old resource stuff that has not yet been removed
#####################################################

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
    from esp.survey.models import ListField

    name = models.CharField(max_length=40)                          #   Brief name
    description = models.TextField()                                #   What is this resource?
    consumable  = models.BooleanField(default = False)              #   Is this consumable?  (Not usable yet. -Michael P)
    priority_default = models.IntegerField(default=-1)  #   How important is this compared to other types?
    only_one = models.BooleanField(default=False, help_text="If set, in some cases, only allow adding one instance of this resource.")
    attributes_pickled  = models.TextField(default="Don't care", blank=True, help_text="A pipe (|) delimited list of possible attribute values.")       
    #   As of now we have a list of string choices for the value of a resource.  But in the future
    #   it could be extended.
    choices = ListField('attributes_pickled')
    program = models.ForeignKey('program.Program', null=True, blank=True)                 #   If null, this resource type is global.  Otherwise it's specific to one program.
    autocreated = models.BooleanField(default=False)

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

    _get_or_create_cache = {}
    @classmethod
    def get_or_create(cls, label, program=None):
        if (label, program) in cls._get_or_create_cache:
            return cls._get_or_create_cache[(label, program)]

        if program:
            base_q = Q(program=program)
            if Tag.getTag('allow_global_restypes'):
                base_q = base_q | Q(program__isnull=True)
        else:
            base_q = Q(program__isnull=True)
        current_type = ResourceType.objects.filter(base_q).filter(name__icontains=label)
        if len(current_type) != 0:
            ret = current_type[0]
        else:
            nt = ResourceType()
            nt.name = label
            nt.description = ''
            nt.attributes_pickled = "Yes"
            nt.program = program
            nt.autocreated = True
            nt.save()
            ret = nt

        cls._get_or_create_cache[(label, program)] = ret
        return ret
        
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
    res_type = models.ForeignKey(ResourceType, on_delete=models.PROTECT)
    desired_value = models.TextField()
    
    def __unicode__(self):
        return 'Resource request of %s for %s: %s' % (unicode(self.res_type), self.target.emailcode(), self.desired_value)

    class Admin:
        pass

class ResourceGroup(models.Model):
    """ A hack to make the database handle resource group ID creation """

    # While in transition, we will need to associate the old ResourceGroup with
    # the new Location.
    location = models.ForeignKey(Location, null=True, blank=True)

    def __unicode__(self):
        return 'Resource group %d' % (self.id,)

    class Admin:
        pass
    
class Resource(models.Model):
    """ An individual resource, such as a class room or piece of equipment.  Categorize by
    res_type, attach to a user if necessary. """
    
    name = models.CharField(max_length=80)
    res_type = models.ForeignKey(ResourceType, on_delete=models.PROTECT)
    num_students = models.IntegerField(blank=True, default=-1)
    # do not use group_id, use res_group instead
    # group_id can be removed with a future migration after all sites
    # have successfully run the migration to res_group
    group_id = models.IntegerField(default=-1)
    res_group = models.ForeignKey(ResourceGroup, null=True, blank=True)
    is_unique = models.BooleanField(default=False)
    user = AjaxForeignKey(ESPUser, null=True, blank=True)
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
        if self.res_group is None:
            #   Make a new group for this
            new_group = ResourceGroup.objects.create()
            self.res_group = new_group
            self.is_unique = True
        else:
            self.is_unique = False

        super(Resource, self).save(*args, **kwargs)

    # I'd love to kill this, but since it's set as the __sub__, it's hard to
    # grep to be sure it's not used.
    def distance(self, other):
        """
        Deprecated.
        """
        warnings.warn("Resource.distance() is deprecated.",
                      DeprecationWarning)
        return 0

    __sub__ = distance


    def identical_resources(self):
        # TODO: update this
        res_list = Resource.objects.filter(name=self.name)
        return res_list

    def associated_resources(self):
        if self.res_group_id is None:
            return Resource.objects.none()
        else:
            return self.res_group.resource_set.exclude(id=self.id)

    def assign_to_section(self, section):
        if self.is_available():
            new_ra = ResourceAssignment()
            new_ra.resource = self
            new_ra.target = section
            new_ra.save()
        else:
            raise ESPError('Attempted to assign class section %d to conflicted resource; and constraint check was on.' % section.id, log=True)
        
    def assignments(self):
        # TODO: remove after old resource forms and schedule_sequence are removed
        return ResourceAssignment.objects.filter(
            resource__res_group__resource=self)
    
    def schedule_sequence(self, program):
        """ Returns a list of strings, which are the status of the room (and its identical
        companions) at each time block belonging to the program. """
        # TODO: update this

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
                
        return sequence

    def available_times(self, program=None):
        event_list = filter(lambda x: self.is_available(timeslot=x), list(self.matching_times(program)))
        return event_list
    
    def matching_times(self, program=None):
        #   Find all times for which a resource of the same name is available.
        event_list = self.identical_resources().values_list('event', flat=True)
        if program:
            return Event.objects.filter(id__in=event_list, program=program).order_by('start')
        else:
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
    is_available.depend_on_row('resources.ResourceAssignment', lambda instance: {'self': instance.resource})
    is_available.depend_on_row('cal.Event', lambda instance: {'timeslot': instance})
    
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
    lock_level = models.IntegerField(default=0)

    def __unicode__(self):
        result = u'Resource assignment for %s' % unicode(self.getTargetOrSubject())
        if self.lock_level > 0:
            result += u' (locked)'
        return result
    
    def getTargetOrSubject(self):
        """ Returns the most finely specified target. (target if it's set, target_subj otherwise) """
        if self.target is not None:
            return self.target
        return self.target_subj
    
    def resources(self):
        return Resource.objects.filter(res_group=self.resource.res_group)
    
    class Admin:
        pass
    
    
def install():
    #   Create default resource types.
    print "Installing esp.resources initial data..."
    if not ResourceType.objects.filter(name='Classroom').exists():
        ResourceType.objects.create(
            name='Classroom',
            description='Type of classroom',
            attributes_pickled='Lecture|Discussion|Outdoor|Lab|Open space',
        )
    if not ResourceType.objects.filter(name='A/V').exists():
        ResourceType.objects.create(
            name='A/V',
            description='A/V equipment',
            attributes_pickled='LCD projector|Overhead projector|Amplified speaker|VCR|DVD player',
        )
    if not ResourceType.objects.filter(name='Computer[s]').exists():
        ResourceType.objects.create(
            name='Computer[s]',
            description='Computer[s]',
            attributes_pickled='ESP laptop|Athena workstation|Macs for students|Windows PCs for students|Linux PCs for students',
        )
    if not ResourceType.objects.filter(name='Seating').exists():
        ResourceType.objects.create(
            name='Seating',
            description='Seating arrangement',
            attributes_pickled="Don't care|Fixed seats|Movable desks",
        )
    if not ResourceType.objects.filter(name='Light control').exists():
        ResourceType.objects.create(
            name='Light control',
            description='Light control',
            attributes_pickled="Don't care|Darkenable",
        )
