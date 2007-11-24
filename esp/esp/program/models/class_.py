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

import datetime
import time

# django Util
from django.db import models
from django.core.cache import cache

# ESP Util
from esp.db.models import Q
from esp.db.models.prepared import ProcedureManager
from esp.db.fields import AjaxForeignKey
from esp.db.cache import GenericCacheHelper

# django models
from django.contrib.auth.models import User

# ESP models
from esp.miniblog.models import Entry
from esp.datatree.models import DataTree, GetNode
from esp.cal.models import Event
from esp.qsd.models import QuasiStaticData
from esp.users.models import ESPUser, UserBit
from esp.program.models import JunctionStudentApp

__all__ = ['Class', 'JunctionAppReview', 'ProgramCheckItem', 'ClassManager', 'ClassCategories']


class ClassCacheHelper(GenericCacheHelper):
    @staticmethod
    def get_key(cls):
        return 'ClassCache__%s' % cls._get_pk_val()


class ClassManager(ProcedureManager):

    def approved(self):
        return self.filter(status = 10)

    def catalog(self, program, ts=None, force_all=False):
        """ Return a queryset of classes for view in the catalog.

        In addition to just giving you the classes, it also
        queries for the category's title (cls.category_txt)
        and the total # of media.
        """

        # some extra queries to save
        select = {'category_txt': 'program_classcategories.category',
                  'media_count': 'SELECT COUNT(*) FROM "qsdmedia_media" WHERE ("qsdmedia_media"."anchor_id" = "program_class"."anchor_id")'}

        where=['program_classcategories.id = program_class.category_id']

        tables=['program_classcategories']
        
        if force_all:
            classes = self.filter(parent_program = program)
        else:
            classes = self.approved().filter(parent_program = program)
            
        if ts is not None:
            classes = classes.filter(meeting_times = ts)

        return classes.extra(select=select,
                             where=where,
                             tables=tables).order_by('category').distinct()

    cache = ClassCacheHelper

class Class(models.Model):

    """ A Class, as taught as part of an ESP program """
    from esp.program.models import Program

    anchor = AjaxForeignKey(DataTree)
    parent_program = models.ForeignKey(Program)
    # title drawn from anchor.friendly_name
    # class number drawn from anchor.name
    category = models.ForeignKey('ClassCategories',related_name = 'cls')
    # teachers are drawn from permissions table
    class_info = models.TextField(blank=True)
    message_for_directors = models.TextField(blank=True)
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    schedule = models.TextField(blank=True)
    prereqs  = models.TextField(blank=True, null=True)
    directors_notes = models.TextField(blank=True, null=True)
    status   = models.IntegerField(default=0)   #   -10 = rejected, 0 = unreviewed, 10 = accepted
    duration = models.FloatField(blank=True, null=True, max_digits=5, decimal_places=2)

    #   Viable times replaced by availability of teacher (function viable_times below)
    #   Resources replaced by resource assignment (functions getResources, getResourceAssignments below)
    meeting_times = models.ManyToManyField(Event, related_name='meeting_times', null=True)

    checklist_progress = models.ManyToManyField('ProgramCheckItem')

    objects = ClassManager()

    def checklist_progress_all_cached(self):
        """ The main Manage page requests checklist_progress.all() O(n) times
        per checkbox in the program.  Minimize the number of these calls that
        actually hit the db. """
        CACHE_KEY = "CLASS__CHECKLIST_PROGRESS__CACHE__%d" % self.id
        val = cache.get(CACHE_KEY)
        if val == None:
            val = self.checklist_progress.all()
            len(val) # force the query to be executed before caching it
            cache.set(CACHE_KEY, val, 1)

        return val




    def __init__(self, *args, **kwargs):
        super(Class, self).__init__(*args, **kwargs)
        self.cache = Class.objects.cache(self)

    class Meta:
        verbose_name_plural = 'Classes'

    def getResourceAssignments(self):
        from esp.resources.models import ResourceAssignment
        return ResourceAssignment.objects.filter(target=self)

    def getResources(self):
        assignment_list = self.getResourceAssignments()
        return [a.resource for a in assignment_list]
    
    def getResourceRequests(self):
        from esp.resources.models import ResourceRequest
        return ResourceRequest.objects.filter(target=self)
    
    def clearResourceRequests(self):
        for rr in self.getResourceRequests():
            rr.delete()
    
    def classroomassignments(self):
        from esp.resources.models import ResourceType
        cls_restype = ResourceType.get_or_create('Classroom')
        return self.getResourceAssignments().filter(target=self, resource__res_type=cls_restype)
    
    def resourceassignments(self):
        #   Get all assignments pertaining to floating resources like projectors.
        return self.getResourceAssignments().filter(target=self, resource__is_unique=True)
    
    def classrooms(self):
        """ Returns the list of classroom resources assigned to this class."""
        from esp.resources.models import Resource

        ra_list = [item['resource'] for item in self.classroomassignments().values('resource')]
        return Resource.objects.filter(id__in=ra_list)

    def initial_rooms(self):
        if self.meeting_times.count() > 0:
            return self.classrooms().filter(event=self.meeting_times.order_by('start')[0]).order_by('id')
        else:
            return None

    def prettyrooms(self):
        """ Return the pretty name of the rooms. """
        if self.meeting_times.count() > 0:
            return [x.name for x in self.initial_rooms()]
        else:
            return []
   
    def starts_soon(self):
        #   Return true if the class's start time is less than 50 minutes after the current time
        #   and less than 10 minutes before the current time.
        first_block = self.start_time()
        if first_block is None:
            return False
        else:
            st = first_block.start
            

        if st is None:
            return False
        else:
            td = time.time() - time.mktime(st.timetuple())
            print td
            if td < 600 and td > -3000:
                return True
            else:
                return False
            
    def already_passed(self):
        start_time = self.start_time()
	if start_time is None:
            return True
        if time.time() - time.mktime(start_time.start.timetuple()) > 600:
            return True
        return False
   
    def start_time(self):
        if self.meeting_times.count() > 0:
            return self.meeting_times.order_by('start')[0]
        else:
            return None
   
    #   Scheduling helper functions
    
    def sufficient_length(self, event_list=None):
        """   This function tells if the class' assigned times are sufficient to cover the duration.
        If the duration is not set, 1 hour is assumed. """
        if self.duration == 0.0:
            duration = 1.0
        else:
            duration = self.duration
        
        if event_list is None:
            event_list = list(self.meeting_times.all().order_by('start'))
        #   If you're 15 minutes short that's OK.
        time_tolerance = 15 * 60
        if Event.total_length(event_list).seconds + time_tolerance < duration * 3600:
            return False
        else:
            return True
    
    def extend_timeblock(self, event, merged=True):
        """ Return the Event list or (merged Event) for this class's duration if the class starts in the
        provided timeslot and continues contiguously until its duration has ended. """
        
        event_list = [event]
        all_events = list(self.parent_program.getTimeSlots())
        event_index = all_events.index(event)

        while not self.sufficient_length(event_list):
            event_index += 1
            event_list.append(all_events[event_index])
            
        if merged:
            return Event.collapse(event_list, tol=datetime.timedelta(minutes=10))
        else:
            return event_list
    
    def scheduling_status(self):
        #   Return a little string that tells you what's up with the resource assignments.
        if not self.sufficient_length():
            return 'Needs time'
        elif self.classrooms().count() < 1:
            return 'Needs room'
        elif self.unsatisfied_requests().count() > 0:
            return 'Needs resources'
        else:
            return 'Happy'
    
    def clear_resource_cache(self):
        from django.core.cache import cache
        from esp.program.templatetags.scheduling import options_key_func
        cache_key1 = 'class__viable_times:%d' % self.id
        cache_key2 = 'class__viable_rooms:%d' % self.id
        cache_key3 = options_key_func(self)
        cache.delete(cache_key1)
        cache.delete(cache_key2)
        cache.delete(cache_key3)
    
    def unsatisfied_requests(self):
        if self.classrooms().count() > 0:
            primary_room = self.classrooms()[0]
            result = primary_room.satisfies_requests(self)
            return result[1]
        else:
            return self.getResourceRequests()
    
    def assign_meeting_times(self, event_list):
        self.meeting_times.clear()
        for event in event_list:
            self.meeting_times.add(event)
    
    def assign_start_time(self, first_event):
        """ Get enough events following the first one until you have the class duration covered.
        Then add them. """
        
        #   This means we have to clear the classrooms.  Sorry.
        self.clearRooms()
        event_list = self.extend_timeblock(first_event, merged=False)
        self.assign_meeting_times(event_list)
    
    def assign_room(self, base_room, compromise=True, clear_others=False):
        """ Assign the classroom given, except at the times needed by this class. """
        rooms_to_assign = base_room.identical_resources().filter(event__in=list(self.meeting_times.all()))
        
        status = True
        errors = []
        
        if clear_others:
            self.clearRooms()
        
        if compromise is False:
            #   Check that the room satisfies all needs of the class.
            result = base_room.satisfies_requests(self)
            if result[0] is False:
                status = False
                errors.append('This room does not have all resources that the class needs (or it is too small) and you have opted not to compromise.  Try a better room.')
        
        if rooms_to_assign.count() != self.meeting_times.count():
            status = False
            errors.append('This room is not available at the times requested by the class.  Bug the webmasters to find out why you were allowed to assign this room.')
        
        for r in rooms_to_assign:
            r.clear_schedule_cache(self.parent_program)
            result = self.assignClassRoom(r)
            if not result:
                status = False
                errors.append('Error: This classroom is already taken.  Please assign a different one.  While you\'re at it, bug the webmasters to find out why you were allowed to assign a conflict.')
            
        return (status, errors)
    
    def viable_times(self):
        """ Return a list of Events for which all of the teachers are available. """
        from django.core.cache import cache
        from esp.resources.models import ResourceType, Resource
        
        def intersect_lists(list_of_lists):
            if len(list_of_lists) == 0:
                return []

            base_list = list_of_lists[0]
            for other_list in list_of_lists[1:]:
                i = 0
                for elt in base_list:
                    if elt not in other_list:
                        base_list.remove(elt)
            return base_list
        
        #   This will need to be cached.
        cache_key = 'class__viable_times:%d' % self.id
        result = cache.get(cache_key)
        if result is not None:
            return result

        teachers = self.teachers()
        num_teachers = teachers.count()
        ta_type = ResourceType.get_or_create('Teacher Availability')

        timeslot_list = []
        for t in teachers:
            timeslot_list.append(list(t.getAvailableTimes(self.parent_program)))
            
        available_times = intersect_lists(timeslot_list)
        
        #   If the class is already scheduled, put its time in.
        if self.meeting_times.count() > 0:
            for k in self.meeting_times.all():
                if k not in available_times:
                    available_times.append(k)
        
        timeslots = Event.group_contiguous(available_times)

        viable_list = []

        for timegroup in timeslots:
            for i in range(0, len(timegroup)):
                #   Check whether there is enough time remaining in the block.
                if self.sufficient_length(timegroup[i:len(timegroup)]):
                    viable_list.append(timegroup[i])
        
        cache.set(cache_key, viable_list)
        return viable_list
    
    def viable_rooms(self):
        """ Returns a list of Resources (classroom type) that satisfy all of this class's resource requests. 
        Resources matching the first time block of the class will be returned. """
        from django.core.cache import cache
        from esp.resources.models import ResourceType, Resource
        import operator
        
        def room_satisfies_times(room, times):
            room_times = room.matching_times()
            satisfaction = True
            for t in times:
                if t not in room_times:
                    satisfaction = False
            return satisfaction
        
        #   This will need to be cached.
        cache_key = 'class__viable_rooms:%d' % self.id
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        #   This function is only meaningful if the times have already been set.  So, back out if they haven't.
        if not self.sufficient_length():
            return None
        
        #   Start with all rooms the program has.  
        #   Filter the ones that are available at all times needed by the class.
        filter_qs = []
        ordered_times = self.meeting_times.order_by('start')
        first_time = ordered_times[0]
        possible_rooms = self.parent_program.getAvailableClassrooms(first_time)
        
        viable_list = filter(lambda x: room_satisfies_times(x, ordered_times), possible_rooms)
            
        cache.set(cache_key, viable_list)
        return viable_list
    
    def clearRooms(self):
        for room in [ra.resource for ra in self.classroomassignments()]:
            room.clear_schedule_cache(self.parent_program)
        self.classroomassignments().delete()
            
    def clearFloatingResources(self):
        self.resourceassignments().delete()

    def assignClassRoom(self, classroom):
        #   Assign an individual resource to this class.
        from esp.resources.models import ResourceAssignment
        
        if classroom.is_taken():
            return False
        else:
            new_assignment = ResourceAssignment()
            new_assignment.resource = classroom
            new_assignment.target = self
            new_assignment.save()
            return True

    def time_created(self):
        #   Return the datetime for when the class was first created.
        #   Oh wait, this is definitely not meh.
        v = GetNode('V/Flags/Registration/Teacher')
        q = self.anchor
        ubl = UserBit.objects.filter(verb=v, qsc=q).order_by('startdate')
        if ubl.count() > 0:
            return ubl[0].startdate
        else:
            return None
        
    def emailcode(self):
        """ Return the emailcode for this class.

        The ``emailcode`` is defined as 'first letter of category' + id.
        """
        return self.category.category[0].upper()+str(self.id)

    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[2:])

    def got_qsd(self):
        return QuasiStaticData.objects.filter(path = self.anchor).values('id').count() > 0
        
    def __str__(self):
        if self.title() is not None:
            return "%s: %s" % (self.id, self.title())
        else:
            return "%s: (none)" % self.id

    def delete(self, adminoverride = False):
        if self.num_students() > 0 and not adminoverride:
            return False

        teachers = self.teachers()
        for teacher in self.teachers():
            self.removeTeacher(teacher)
            self.removeAdmin(teacher)

        if self.anchor:
            self.anchor.delete(True)

        self.meeting_times.clear()
        super(Class, self).delete()
        

    def cache_time(self):
        return 99999
    
    def title(self):

        retVal = self.cache['title']

        if retVal:
            return retVal
        
        retVal = self.anchor.friendly_name

        self.cache['title'] = retVal

        return retVal
    
    def teachers(self, use_cache = True):
        """ Return a queryset of all teachers of this class. """
        retVal = self.cache['teachers']
        if retVal is not None and use_cache:
            return retVal
        
        v = GetNode('V/Flags/Registration/Teacher')

        retVal = UserBit.objects.bits_get_users(self.anchor, v, user_objs=True)

        list(retVal)
        
        self.cache['teachers'] = retVal
        return retVal

    def cannotAdd(self, user, checkFull=True, request=False, use_cache=True):
        """ Go through and give an error message if this user cannot add this class to their schedule. """
        if not user.isStudent():
            return 'You are not a student!'
        
        if not self.isAccepted():
            return 'This class is not accepted.'

#        if checkFull and self.parent_program.isFull(use_cache=use_cache) and not ESPUser(user).canRegToFullProgram(self.parent_program):
        if checkFull and self.parent_program.isFull(use_cache=True) and not ESPUser(user).canRegToFullProgram(self.parent_program):
            return 'This programm cannot accept any more students!  Please try again in its next session.'

        if checkFull and self.isFull(use_cache=use_cache):
            return 'Class is full!'

        if request:
            verb_override = request.get_node('V/Flags/Registration/GradeOverride')
            verb_conf = request.get_node('V/Flags/Registration/Confirmed')
            verb_prelim = request.get_node('V/Flags/Registration/Preliminary')
        else:
            verb_override = GetNode('V/Flags/Registration/GradeOverride')
            verb_conf = GetNode('V/Flags/Registration/Confirmed')
            verb_prelim = GetNode('V/Flags/Registration/Preliminary')            

        if user.getGrade() < self.grade_min or \
               user.getGrade() > self.grade_max:
            if not UserBit.UserHasPerms(user = user,
                                        qsc  = self.anchor,
                                        verb = verb_override):
                return 'You are not in the requested grade range for this class.'

        # student has no classes...no conflict there.
        if user.getEnrolledClasses(self.parent_program, request).count() == 0:
            return False

        if user.isEnrolledInClass(self, request):
            return 'You are already signed up for this class!'

        # check to see if there's a conflict:
        for cls in user.getEnrolledClasses(self.parent_program, request):
            for time in cls.meeting_times.all():
                if self.meeting_times.filter(id = time.id).count() > 0:
                    return 'Conflicts with your schedule!'

        # this use *can* add this class!
        return False

    def makeTeacher(self, user):
        v = GetNode('V/Flags/Registration/Teacher')
        
        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)
        ub.save()
        return True

    def removeTeacher(self, user):
        v = GetNode('V/Flags/Registration/Teacher')

        UserBit.objects.filter(user = user,
                               qsc = self.anchor,
                               verb = v).delete()
        return True

    def subscribe(self, user):
        v = GetNode('V/Subscribe')

        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)

        return True
    
    def makeAdmin(self, user, endtime = None):
        v = GetNode('V/Administer/Edit')

        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)


        return True        


    def removeAdmin(self, user):
        v = GetNode('V/Administer/Edit')
        UserBit.objects.filter(user = user,
                               qsc = self.anchor,
                               verb = v).delete()
        return True

    def conflicts(self, teacher):
        from esp.users.models import ESPUser
        user = ESPUser(teacher)
        if user.getTaughtClasses().count() == 0:
            return False
        
        for cls in user.getTaughtClasses().filter(parent_program = self.parent_program):
            for time in cls.meeting_times.all():
                if self.meeting_times.filter(id = time.id).count() > 0:
                    return True

    def students(self, use_cache=True):
        retVal = self.cache['students']
        if retVal is not None and use_cache:
            return retVal

        v = GetNode( 'V/Flags/Registration/Preliminary' )

        retVal = UserBit.objects.bits_get_users(self.anchor, v, user_objs=True)
        
        list(retVal)

        self.cache['students'] = retVal
        return retVal
    

    @staticmethod
    def idcmp(one, other):
        return cmp(one.id, other.id)

    @staticmethod
    def catalog_sort(one, other):
        cmp1 = cmp(one.category.category, other.category.category)
        if cmp1 != 0:
            return cmp1
        return cmp(one, other)
    
    def __cmp__(self, other):
        selfevent = self.firstBlockEvent()
        otherevent = other.firstBlockEvent()

        if selfevent is not None and otherevent is None:
            return 1
        if selfevent is None and otherevent is not None:
            return -1

        if selfevent is not None and otherevent is not None:
            cmpresult = selfevent.__cmp__(otherevent)
            if cmpresult != 0:
                return cmpresult

        return cmp(self.title(), other.title())


    def firstBlockEvent(self):
        eventList = self.meeting_times.all().order_by('start')
        if eventList.count() == 0:
            return None
        else:
            return eventList[0]

    def num_students(self, use_cache=True):
        retVal = self.cache['num_students']
        if retVal is not None and use_cache:
            return retVal

        if use_cache:
            retValCache = self.cache['students']
            if retValCache != None:
                retVal = len(retValCache)
                cache['num_students'] = retVal
                return retVal

        v = GetNode( 'V/Flags/Registration/Preliminary' )

        retVal = UserBit.objects.bits_get_users(self.anchor, v, user_objs=True).count()

        self.cache['num_students'] = retVal
        return retVal            


    def isFull(self, use_cache=True):
        if self.num_students(use_cache=use_cache) >= self.class_size_max:
            return True
        else:
            return False
    
    def getTeacherNames(self):
        teachers = []
        for teacher in self.teachers():
            name = '%s %s' % (teacher.first_name,
                              teacher.last_name)

            if name.strip() == '':
                name = teacher.username
            teachers.append(name)
        return teachers

    def friendly_times(self, use_cache=True):
        """ Return a friendlier, prettier format for the times.

        If the events of this class are next to each other (within 10-minute overlap,
        the function will automatically collapse them. Thus, instead of
           ['11:00am--12:00n','12:00n--1:00pm'],
           
        you would get
           ['11:00am--1:00pm']
        for instance.
        """
        from esp.cal.models import Event
        from esp.resources.models import ResourceAssignment, ResourceType, Resource

        retVal = self.cache['friendly_times']

        if retVal is not None and use_cache:
            return retVal
            
        txtTimes = []
        eventList = []
        
        # For now, use meeting times lookup instead of resource assignments.
        """
        classroom_type = ResourceType.get_or_create('Classroom')
        resources = Resource.objects.filter(resourceassignment__target=self).filter(res_type=classroom_type)
        events = [r.event for r in resources] 
        """
        events = list(self.meeting_times.all())

        txtTimes = [ event.short_time() for event
                     in Event.collapse(events, tol=datetime.timedelta(minutes=10)) ]

        self.cache['friendly_times'] = txtTimes

        return txtTimes
            

    def update_cache_students(self):
        from esp.program.templatetags.class_render import cache_key_func, core_cache_key_func
        cache.delete(core_cache_key_func(self))
        cache.delete(cache_key_func(self))

        self.cache.update()


    def update_cache(self):
        from esp.program.templatetags.class_render import cache_key_func, core_cache_key_func
        cache.delete(cache_key_func(self))
        cache.delete(core_cache_key_func(self))
        
        from esp.program.templatetags.class_manage_row import cache_key as class_manage_row_cache_key
        cache.delete(class_manage_row_cache_key(self, None)) # this cache_key doesn't actually care about the program, as classes can only be associated with one program.  If we ever change this, update this function call.

        self.teachers(use_cache = False)

        self.cache.update()

    def unpreregister_student(self, user):

        prereg_verb = GetNode('V/Flags/Registration/Preliminary')

        for ub in UserBit.objects.filter(user=user, qsc=self.anchor_id, verb=prereg_verb):
            ub.delete()

        # update the students cache
        students = list(self.students())
        students = [ student for student in students
                     if student.id != user.id ]
        self.cache['students'] = students
        

    def preregister_student(self, user, overridefull=False):

        prereg_verb = GetNode( 'V/Flags/Registration/Preliminary' )

                
        if overridefull or not self.isFull():
            #    Then, create the userbit denoting preregistration for this class.
            UserBit.objects.get_or_create(user = user, qsc = self.anchor,
                                          verb = prereg_verb)

            # update the students cache
            students = list(self.students())
            students.append(ESPUser(user))
            self.cache['students'] = students
            

            self.update_cache_students()
            return True
        else:
            #    Pre-registration failed because the class is full.
            return False

    def pageExists(self):
        from esp.qsd.models import QuasiStaticData
        return len(self.anchor.quasistaticdata_set.filter(name='learn:index').values('id')[:1]) > 0

    def prettyDuration(self):
        if self.duration is None:
            return 'N/A'

        return '%s:%02d' % \
               (int(self.duration),
            int((self.duration - int(self.duration)) * 60))


    def isAccepted(self):
        return self.status == 10

    def isReviewed(self):
        return self.status != 0

    def isRejected(self):
        return self.status == -10

    def accept(self, user=None, show_message=False):
        """ mark this class as accepted """
        if self.isAccepted():
            return False # already accepted

        self.status = 10
        self.save()

        if not show_message:
            return True

        subject = 'Your %s class was approved!' % (self.parent_program.niceName())
        
        content =  """Congratulations, your class,
%s,
was approved! Please go to http://esp.mit.edu/teach/%s/class_status/%s to view your class' status.

-esp.mit.edu Autogenerated Message""" % \
                  (self.title(), self.parent_program.getUrlBase(), self.id)
        if user is None:
            user = AnonymousUser()
        Entry.post(user, self.anchor.tree_create(['TeacherEmail']), subject, content, True)       
        return True

    def propose(self):
        """ Mark this class as just `proposed' """
        self.status = 0
        self.save()

    def reject(self):
        """ Mark this class as rejected """
        verb = GetNode('V/Flags/Registration/Preliminary')

        self.anchor.userbit_qsc.filter(verb = verb).delete()
        self.status = -10
        self.save()

            
    def docs_summary(self):
        """ Return the first three documents associated
        with a class, for previewing. """

        retVal = self.cache['docs_summary']

        if retVal is not None:
            return retVal

        retVal = self.anchor.media_set.all()[:3]
        list(retVal)

        self.cache['docs_summary'] = retVal

        return retVal
            
    def getUrlBase(self):
        """ gets the base url of this class """
        tmpnode = self.anchor
        urllist = []
        while tmpnode.name != 'Programs':
            urllist.insert(0,tmpnode.name)
            tmpnode = tmpnode.parent
        return "/".join(urllist)

    def save(self):
        self.update_cache()
        super(Class, self).save()
                               
    class Admin:
        pass
    
    class Meta:
        app_label = 'program'
        db_table = 'program_class'

class JunctionAppReview(models.Model):
    cls = models.ForeignKey(Class)
    junctionapp = models.ForeignKey(JunctionStudentApp)
    student     = AjaxForeignKey(User)
    score = models.IntegerField(blank=True,null=True)
    create_ts = models.DateTimeField(default = datetime.datetime.now,
                                     editable = False)

    def __str__(self):
        return "Review for %s in class %s" % (self.cls, self.student)
    
    class Meta:
        app_label = 'program'
        db_table = 'program_junctionappreview'

    class Admin:
        pass


    class Admin:
        pass

class ProgramCheckItem(models.Model):
    from esp.program.models import Program
    
    program = models.ForeignKey(Program, related_name='checkitems')
    title   = models.CharField(maxlength=512)
    seq     = models.PositiveIntegerField(blank=True,verbose_name='Sequence',
                                          help_text = 'Lower is earlier')

    def save(self, *args, **kwargs):
        if self.seq is None:
            try:
                item = ProgramCheckItem.objects.filter(program = self.program).order_by('-seq')[0]
                self.seq = item.seq + 5
            except IndexError:
                self.seq = 0
        super(ProgramCheckItem, self).save(*args, **kwargs)

    def __str__(self):
        return '%s for "%s"' % (self.title, str(self.program).strip())

    class Admin:
        pass

    class Meta:
        ordering = ('seq',)
        app_label = 'program'
        db_table = 'program_programcheckitem'


class ClassCategories(models.Model):
    """ A list of all possible categories for an ESP class

    Categories include 'Mathematics', 'Science', 'Zocial Zciences', etc.
    """
    category = models.TextField()

    class Meta:
        verbose_name_plural = 'Class Categories'
        app_label = 'program'
        db_table = 'program_classcategories'

    def __str__(self):
        return str(self.category)
        
        
    @staticmethod
    def category_string(letter):
        
        results = ClassCategories.objects.filter(category__startswith = letter)
        
        if results.count() == 1:
            return results[0].category
        else:
            return None

    class Admin:
        pass
