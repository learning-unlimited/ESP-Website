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

from esp.program.models import Program, JunctionStudentApp

__all__ = ['Class', 'JunctionAppReview', 'ClassRoomAssignment',
           'ProgramCheckItem', 'ClassTimeSlot', 'ClassManager',
           'ResourceRequest','ClassCategories']


class ClassCacheHelper(GenericCacheHelper):
    @staticmethod
    def get_key(cls):
        return 'ClassCache__%s' % cls._get_pk_val()


class ClassManager(ProcedureManager):

    def approved(self):
        return self.filter(status = 10)

    def catalog(self, program, ts=None):
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
        
        classes = self.approved().filter(parent_program = program)

        if ts is not None:
            classes = classes.filter(meeting_times = ts)

        return classes.extra(select=select,
                             where=where,
                             tables=tables).order_by('category').distinct()

    cache = ClassCacheHelper

class Class(models.Model):

    """ A Class, as taught as part of an ESP program """

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
    status   = models.IntegerField(default=0)
    duration = models.FloatField(blank=True, null=True, max_digits=5, decimal_places=2)
    event_template = AjaxForeignKey(DataTree, related_name='class_event_template_set', null=True)
    meeting_times = models.ManyToManyField(DataTree, related_name='meeting_times', null=True)
    viable_times = models.ManyToManyField(DataTree, related_name='class_viable_set', blank=True)
    meeting_timeslots = models.ManyToManyField('ClassTimeSlot', related_name='meeting_timeslots', null=True, blank=True)
    viable_timeslots  = models.ManyToManyField('ClassTimeSlot', related_name='viable_timeslots', null=True, blank=True)    
    resources = models.ManyToManyField(DataTree, related_name='class_resources', blank=True)

    checklist_progress = models.ManyToManyField('ProgramCheckItem')

    #    We think this is useless because the sign-up is completely based on userbits.
    enrollment = models.IntegerField()

    objects = ClassManager()

    def __init__(self, *args, **kwargs):
        super(Class, self).__init__(*args, **kwargs)
        self.cache = Class.objects.cache(self)

    class Meta:
        verbose_name_plural = 'Classes'

    def classroomassignments(self):
        return ClassRoomAssignment.objects.filter(cls = self)

    def classrooms(self):
        """ Returns the class rooms tree nodes for this class."""
        return DataTree.objects.filter(room__cls = self).distinct()

    def prettyrooms(self):
        """ Return the pretty name of the rooms.

        Could use generators here, but not worth it.
        """
        return [x.friendly_name for x in self.classrooms()]

    def clearRooms(self):
        """ Delete all rooms for this class. """
        ClassRoomAssignment.objects.filter(cls = self).delete()

    def assignClassRoom(self, classroom):
        self.clearRooms()

        for time in self.meeting_times.all():
            ClassRoomAssignment.objects.create(cls = self,
                                               timeslot = time,
                                               room = classroom)
        return True

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

    def PopulateEvents(self):
        """ Given this instance's event_template, generate a series of events that define this class's schedule """
        for e in self.event_template.event_set.all():
            newevent = Event()
            newevent.start = e.start
            newevent.end = e.end
            newevent.short_description = e.short_description
            newevent.description = e.description.replace('[event]', e.anchor.friendly_name) # Allow for the insertion of event names, so that the templates are less generic/nonspecific
            newevent.event_type = e.event_type
            newevent.anchor = self.anchor
            newevent.save()
        
    def __str__(self):
        if self.title() is not None:
            return self.title()
        else:
            return ""

    def delete(self, adminoverride = False):
        if self.num_students() > 0 and not adminoverride:
            return False

        teachers = self.teachers()
        for teacher in self.teachers():
            self.removeTeacher(teacher)
            self.removeAdmin(teacher)


        if self.anchor:
            self.anchor.delete(True)
        
        self.viable_times.clear()
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

    def cannotAdd(self, user, checkFull=True, request=False):
        """ Go through and give an error message if this user cannot add this class to their schedule. """
        if not user.isStudent():
            return 'You are not a student!'
        
        if not self.isAccepted():
            return 'This class is not accepted.'

        if checkFull and self.parent_program.isFull():
            return 'This programm cannot accept any more students!  Please try again in its next session.'

        if checkFull and self.isFull():
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
        eventList = []
        for timeanchor in self.meeting_times.all():
            events = Event.objects.filter(anchor=timeanchor)
            if len(events) == 1:
                eventList.append(events[0])
        if len(eventList) == 0:
            return None
        eventList.sort()
        return eventList[0]

    def num_students(self):
        return len(self.students())

    def isFull(self):
        if self.num_students() >= self.class_size_max:
            return True
        else:
            return False
    
    def getTeacherNames(self):
        teachers = []
        for teacher in self.teachers():
            try:
                contact = teacher.getLastProfile().contact_user
                name = '%s %s' % (contact.first_name,
                                  contact.last_name)
            except:
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

        retVal = self.cache['friendly_times']

        if retVal is not None and use_cache:
            return retVal
            
        txtTimes = []
        eventList = []
        events = list(Event.objects.filter(anchor__meeting_times = self))

        txtTimes = [ event.pretty_time() for event
                     in Event.collapse(events) ]

        self.cache['friendly_times'] = txtTimes

        return txtTimes
            

    def update_cache_students(self):
        from esp.program.templatetags.class_render import cache_key_func
        cache.delete(cache_key_func(self))

        self.cache.update()


    def update_cache(self):
        from esp.program.templatetags.class_render import cache_key_func
        cache.delete(cache_key_func(self))
        
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
            

            #self.update_cache_students()
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

class ClassRoomAssignment(models.Model):
    """ This associates a class, with a room, with a timeblock
        This will prevent problems with classes that have to move """
    room     = AjaxForeignKey(DataTree, related_name="room")
    timeslot = AjaxForeignKey(DataTree, related_name="timeslot")
    unique_together = (('room','timeslot'),)
    cls      = models.ForeignKey(Class)
    
    class Meta:
        app_label = 'program'
        db_table = 'program_classroomassignment'

class ClassTimeSlot(models.Model):
    """
    A time slot for a particular class and program.
    """
    program = models.ForeignKey(Program, editable=False)
    event   = models.ForeignKey(Event)
    description = models.CharField(maxlength=256, blank=True, null=True)
    
    def __str__(self):
        if self.description:
            return self.description
        else:
            return str(self.event)

    class Meta:
        app_label = 'program'
        db_table = 'program_classtimeslot'

class ProgramCheckItem(models.Model):

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

class ResourceRequest(models.Model):
    """ An indication of resources requested for a particular class """
    requestor = models.OneToOneField(Class)
    wants_projector = models.BooleanField()
    wants_computer_lab = models.BooleanField()
    wants_open_space = models.BooleanField()

    def __str__(self):
        return 'Resource request for ' + str(self.requestor)

    class Admin:
        pass

    class Meta:
        app_label = 'program'
        db_table = 'program_resourcerequest'


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
