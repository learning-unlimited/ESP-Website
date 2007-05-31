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
from django.contrib.auth.models import User, AnonymousUser
from esp.cal.models import Event
from esp.datatree.models import DataTree, GetNode
from esp.users.models import UserBit, ContactInfo, StudentInfo, TeacherInfo, EducatorInfo, GuardianInfo
from esp.lib.markdown import markdown
from esp.qsd.models import QuasiStaticData
from datetime import datetime
from django.core.cache import cache
from esp.miniblog.models import Entry
from django.db.models import Q
from esp.db.fields import AjaxForeignKey

# Create your models here.
class ProgramModule(models.Model):
    """ Program Modules for a Program """

    # Title for the link displayed for this Program Module in the Programs form
    link_title = models.CharField(maxlength=64, blank=True, null=True)

    # Human-readable name for the Program Module
    admin_title = models.CharField(maxlength=128)

    # Main view function associated with this Program Module
    main_call  = models.CharField(maxlength=32)

    # aseering 3-19-2007 -- ??; no idea what this is for
    check_call = models.CharField(maxlength=32, blank=True, null=True)

    # One of teach/learn/etc.; What is this module typically used for?
    module_type = models.CharField(maxlength=32)

    # self.__name__, stored neatly in the database
    handler    = models.CharField(maxlength=32)

    # Sequence orderer.  When ProgramModules are listed on a page, order them
    # from smallest to largest 'seq' value
    seq = models.IntegerField()

    # Secondary view functions associated with this ProgramModule
    aux_calls = models.CharField(maxlength=512, blank=True, null=True)

    # Summary view functions, that summarize data for all instances of this ProgramModule
    summary_calls = models.CharField(maxlength=512, blank=True, null=True)

    # Must the user supply this ProgramModule with data in order to complete program registration?
    required = models.BooleanField()

    def getFriendlyName(self):
        """ Return a human-readable name that identifies this Program Module """
        return self.admin_title

    def getSummaryCalls(self):
        """
        Returns a list of the summary view functions for the specified module

        Only returns functions that are both listed in summary_calls,
        and that are valid functions for this class.

        Returns an empty list if no calls are found.
        """
        callNames = this.summary_calls.split(',')

        calls = []
        myClass = this.getPythonClass()

             

        for i in callNames:
            try:
                calls.append(getattr(myClass, i))
            except:
                pass

        return calls


    def getPythonClass(self):
        """
        Gets the Python class that's associated with this ProgramModule database record

        The file 'esp/program/module/handlers/[self.handler]' must contain
        a class named [self.handler]; we return that class.

        Raises a PrograModule.CannotGetClassException() if the class can't be imported.
        """
        try:
            path = "esp.program.modules.handlers.%s" % (self.handler.lower())
            mod = __import__(path, (), (), [self.handler])
            return getattr(mod, self.handler)
        except ImportError:
            raise ProgramModule.CannotGetClassException('Could not import: '+path)
        except AttributeError:
            raise ProgramModule.CannotGetClassException('Could not get class: '+path)

    class CannotGetClassException(Exception):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return self.msg
    
    def __str__(self):
        return 'Program Module "%s"' % self.admin_title

    class Admin:
        pass
    
class ArchiveClass(models.Model):
    """ Old classes throughout the years """
    program = models.CharField(maxlength=256)
    year = models.IntegerField()
    date = models.CharField(maxlength=128)
    category = models.CharField(maxlength=16)
    teacher = models.CharField(maxlength=1024)
    title = models.CharField(maxlength=1024)
    description = models.TextField()
    teacher_ids = models.CharField(maxlength=256, blank=True, null=True)
    student_ids = models.TextField()
    
    num_old_students = models.IntegerField(default=0)

    #def __str__(self):
    #    return '"%s" taught by "%s"' % (self.title, self.teacher)

    def __cmp__(self, other):
        test = cmp(self.year, other.year)
        if test != 0:
            return test
        test = cmp(self.date, other.date)
        if test != 0:
            return test
        test = cmp(self.title, other.title)
        if test != 0:
            return test
        return 0
    
    def heading(self):
        return ({'label': 'Teacher', 'value': self.teacher},
            {'label': 'Year', 'value': self.year},
            {'label': 'Program', 'value': self.program},
            {'label': 'Category', 'value': self.category})
    
    def content(self):
        return self.description

    def __str__(self):
        from django.template import loader, Context
        t = loader.get_template('models/ArchiveClass.html')
        return t.render({'class': self})
        
    def num_students(self):
        if self.student_ids is not None:
            return len(self.student_ids.strip('|').split('|')) + self.num_old_students
        else:
            return self.num_old_students
    
    def add_students(self, users):
        if self.student_ids is not None:
            self.student_ids += '%s|' % '|'.join([str(u.id) for u in users])
        else:
            self.student_ids = '|%s|' % '|'.join([str(u.id) for u in users])
            
    def add_teachers(self, users):
        if self.teacher_ids is not None:
            self.teacher_ids += '%s|' % '|'.join([str(u.id) for u in users])
        else:
            self.teacher_ids = '|%s|' % '|'.join([str(u.id) for u in users])
        
    def students(self):
        from esp.users.models import ESPUser
        userlist = []
        for uid in self.student_ids.strip('|').split('|'):
            userlist += ESPUser.objects.filter(id = uid)
        return userlist
    
    def teachers(self):
        from esp.users.models import ESPUser
        userlist = []
        for uid in self.teacher_ids.strip('|').split('|'):
            userlist += ESPUser.objects.filter(id = uid)
        return userlist
    
    @staticmethod
    def getForUser(user):
        """ Get a list of archive classes for a specific user. """
        from esp.db.models import Q
        Q_ClassTeacher = Q(teacher__icontains = (user.first_name + ' ' + user.last_name)) |\
               Q(teacher_ids__icontains = ('|%s|' % user.id))
        Q_ClassStudent = Q(student_ids__icontains = ('|%s|' % user.id))
        Q_Class = Q_ClassTeacher | Q_ClassStudent
        return ArchiveClass.objects.filter(Q_Class).order_by('-year','-date','title')
    

    
    
class Program(models.Model):
    """ An ESP Program, such as HSSP Summer 2006, Splash Fall 2006, Delve 2005, etc. """
    anchor = AjaxForeignKey(DataTree) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    director_email = models.CharField(maxlength=64)
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    program_modules = models.ManyToManyField(ProgramModule)


    def _get_type_url(self, type):
        return '/%s/%s/' % (type, '/'.join(self.anchor.tree_encode()[2:]))

    def __init__(self, *args, **kwargs):
        retVal = super(Program, self).__init__(*args, **kwargs)

        for type in ['teach','learn','manage','onsite']:
            setattr(self, 'get_%s_url' % type, self._get_type_url(type))

        return retVal


    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[2:])
    
    def __str__(self):
        return str(self.anchor.parent.friendly_name) + ' ' + str(self.anchor.friendly_name)

    def parent(self):
        return anchor.parent

    def niceName(self):
        return str(self).replace("_", " ")

    def niceSubName(self):
        return self.anchor.name.replace('_', ' ')

    def getUrlBase(self):
        """ gets the base url of this class """
        tmpnode = self.anchor
        urllist = []
        while tmpnode.name != 'Programs':
            urllist.insert(0,tmpnode.name)
            tmpnode = tmpnode.parent
        return "/".join(urllist)
                      

    def teacherSubscribe(self, user):
        v = GetNode('V/Subscribe')
        qsc = self.anchor.tree_create(['Announcements',
                           'Teachers'])
        
        if UserBit.objects.filter(user = user,
                      qsc = qsc,
                      verb = v).count() > 0:
            return False

        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = qsc,
                                verb = v)
        return True


    def get_msg_vars(self, user, key):
        modules = self.getModules(user)
        for module in modules:
            retVal = module.get_msg_vars(user, key)
            if retVal is not None and len(str(retVal).strip()) > 0:
                return retVal

        return ''
    
    def teachers(self, QObjects = False):
        modules = self.getModules(None)
        teachers = {}
        for module in modules:
            tmpteachers = module.teachers(QObjects)
            if tmpteachers is not None:
                teachers.update(tmpteachers)
        return teachers

    def students(self, QObjects=False):
        modules = self.getModules(None)
        students = {}
        for module in modules:
            tmpstudents = module.students(QObjects)
            if tmpstudents is not None:
                students.update(tmpstudents)
        return students

    def getLists(self, QObjects=False):
        lists = self.students(QObjects)
        lists.update(self.teachers(QObjects))
        learnmodules = self.getModules(None)
        teachmodules = self.getModules(None)

        
        for k, v in lists.items():
            lists[k] = {'list': v,
                        'description':''}

        desc  = {}
        for module in learnmodules:
            tmpdict = module.studentDesc()
            if tmpdict is not None:
                desc.update(tmpdict)
        for module in teachmodules:
            tmpdict = module.teacherDesc()
            print tmpdict
            if tmpdict is not None:
                desc.update(tmpdict)

        for k, v in desc.items():
            lists[k]['description'] = v
        from esp.users.models import ESPUser
        usertypes = ['Student', 'Teacher', 'Guardian', 'Educator']

        

        for usertype in usertypes:
            lists['all_'+usertype.lower()+'s'] = {'description':
                                   usertype+'s in all of ESP',
                                   'list' : ESPUser.getAllOfType(usertype)}

        lists['emaillist'] = {'description':
                      """All users in our mailing list without an account.""",
                      'list': Q(password = 'emailuser')}
            
        return lists

    def students_union(self, QObject = False):
        import operator
        if len(self.students().values()) == 0:
            if QObject:
                return Q(id = -1)
            else:
                return User.objects.filter(id = -1)
                    
        union = reduce(operator.or_, [x for x in self.students(True).values() ])
        if QObject:
            return union
        else:
            return User.objects.filter(union).distinct()


    def teachers_union(self, QObject = False):
        import operator
        if len(self.teachers().values()) == 0:
            return []
        union = reduce(operator.or_, [x for x in self.teachers(True).values() ])
        if QObject:
            return union
        else:
            return User.objects.filter(union).distinct()    

    def num_students(self):
        modules = self.getModules(None, 'learn')
        students = {}
        for module in modules:
            tmpstudents = module.students()
            if tmpstudents is not None:
                for k, v in tmpstudents.items():
                    if type(v) == list:
                        students[k] = len(v)
                    else:
                        students[k] = v.count()
        return students

    def classes_node(self):
        return DataTree.objects.get(parent = self.anchor, name = 'Classes')

    def getTimeSlots(self):
        return list(self.anchor.tree_create(['Templates','TimeSlots']).children().order_by('id'))

    def isConfirmed(self, espuser):
        v = GetNode('V/Flags/Public')
        userbits = UserBit.objects.filter(verb = v, user = espuser,
                         qsc = self.anchor.tree_create(['Confirmation']))
        if len(userbits) < 1:
            return False

        return True
    
    def getClassRooms(self):
        return list(self.anchor.tree_create(['Templates','Classrooms']).children().order_by('name'))

    def addClassRoom(self, roomname, shortname):
        room = DataTree()
        room.parent = self.anchor.tree_create(['Templates','Classrooms'])
        room.name = shortname
        room.friendly_name = roomname
        room.save()

    def classes(self):
        return Class.objects.filter(parent_program = self)        

    def getResources(self):
        return list(self.anchor.tree_create(['Templates','Resources']).children())

    def getModules(self, user = None, tl = None):
        """ Gets a list of modules for this program. """
        from esp.program.modules import base

        cache_key = "PROGRAMMODULES__%s__%s" % (self.id, tl)

        retVal = cache.get(cache_key)

        if not retVal:

            def cmpModules(mod1, mod2):
                """ comparator function for two modules """
                try:
                    return cmp(mod1.seq, mod2.seq)
                except AttributeError:
                    return 0
            if tl:
                modules =  [ base.ProgramModuleObj.getFromProgModule(self, module)
                     for module in self.program_modules.filter(module_type = tl) ]
            else:
                modules =  [ base.ProgramModuleObj.getFromProgModule(self, module)
                     for module in self.program_modules.all()]

            modules.sort(cmpModules)

            cache.set(cache_key, modules, 9999)
        else:
            modules = retVal
        
        if user:
            for module in modules:
                module.setUser(user)
        return modules
        
    class Admin:
        pass
    
    @staticmethod
    def find_by_perms(user, verb):
        """ Fetch a list of relevant programs for a given user and verb """
        return UserBit.find_by_anchor_perms(Program,user,verb)



class ClassCategories(models.Model):
    """ A list of all possible categories for an ESP class

    Categories include 'Mathematics', 'Science', 'Zocial Zciences', etc.
    """
    category = models.TextField()
    class Meta:
        verbose_name_plural = 'Class Categories'
        
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


class ClassManager(models.Manager):

    def approved(self):
        return self.filter(status = 10)

# FIXME: The Class object should use the permissions system to control
# which grades (Q/Community/6_12/*) are permitted to join the class, though
# the UI should make it as clean as two numbers, at least initially.
class Class(models.Model):
    """ A Class, as taught as part of an ESP program """
    anchor = AjaxForeignKey(DataTree)
    parent_program = models.ForeignKey(Program)
    # title drawn from anchor.friendly_name
    # class number drawn from anchor.name
    category = models.ForeignKey(ClassCategories)
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

    class Meta:
        verbose_name_plural = 'Classes'

    def classroomassignments(self):
        return ClassRoomAssignment.objects.filter(cls = self)

    def classrooms(self):
        assignments = ClassRoomAssignment.objects.filter(cls = self)
        rooms = {}
        if assignments.count() == 0:
            return []
        
        for assignment in assignments:
            rooms[assignment.room.id] = assignment.room

        return rooms.values()

    def prettyrooms(self):
        return [ x.friendly_name  for x in self.classrooms() ]

    def clearRooms(self):
        for x in ClassRoomAssignment.objects.filter(cls = self):
            x.delete()        

    def assignClassRoom(self, classroom):
        self.clearRooms()

        for time in self.meeting_times.all():
            roomassignment = ClassRoomAssignment()
            roomassignment.cls = self
            roomassignment.timeslot = time
            roomassignment.room = classroom
            roomassignment.save()
        return True
        

    def emailcode(self):
        return self.category.category[0].upper()+str(self.id)

    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[2:])

    def got_qsd(self):
        return (QuasiStaticData.objects.filter(path = self.anchor).count() > 0)

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
        cache_id = 'Class__'+str(self.id)

        retVal = cache.get(cache_id)
        if retVal is not None and type(retVal) == dict and retVal.has_key('title'):
            return retVal['title']
        if type(retVal) != dict:
            retVal = {}
            
        retVal['title'] = self.anchor.friendly_name
        
        cache.set(cache_id, retVal, self.cache_time())
        return retVal['title']
    
    def teachers(self, use_cache = True):

        cache_id = 'Class__' + str(self.id)

        retVal   = cache.get(cache_id)

        if use_cache and (retVal is not None) and \
          (type(retVal) == dict) and retVal.has_key('teachers'):
            if retVal['teachers'] != []:
                return retVal['teachers']
        
        if type(retVal) != dict:
            retVal = {}
        #retVal = {}
            
        from esp.users.models import ESPUser
        v = GetNode( 'V/Flags/Registration/Teacher' )
        userbits = [ x.user_id for x in UserBit.bits_get_users( self.anchor, v) ]
                
        if len(userbits) > 0:
            teachers = list(User.objects.filter(id__in=userbits).distinct())
            retVal['teachers'] = map(ESPUser, teachers)
        else:
            retVal['teachers'] = []

        cache.set(cache_id, retVal, self.cache_time())

        return retVal['teachers']
              
        #return [ x.user for x in UserBit.bits_get_users( self.anchor, v ) ]

    def manage_finished(self):
        verb = GetNode('V/Flags/Class/Finished')
        return UserBit.UserHasPerms(user = None,
                        qsc  = self.anchor,
                        verb = verb)
    
    def teacher_interviewed(self):
        verb = GetNode('V/Flags/Class/Interviewed')
        print verb
        return UserBit.UserHasPerms(user = None,
                        qsc  = self.anchor,
                        verb = verb)

    def manage_scheduled(self):
        verb = GetNode('V/Flags/Class/Scheduled')
        return UserBit.UserHasPerms(user = None,
                        qsc  = self.anchor,
                        verb = verb)
    

    def manage_roomassigned(self):
        verb = GetNode('V/Flags/Class/RoomAssigned')
        return UserBit.UserHasPerms(user = None,
                        qsc  = self.anchor,
                        verb = verb)
    



    def cannotAdd(self, user, checkFull=True):
        """ Go through and give an error message if this user cannot add this class to their schedule. """
        if not user.isStudent():
            return 'You are not a student!'
        
        if not self.isAccepted():
            return 'This class is not accepted.'

        if checkFull and self.isFull():
            return 'Class is full!'


        verb_override = GetNode('V/Flags/Registration/GradeOverride')
        
        if not UserBit.UserHasPerms(user = user,
                          qsc  = self.anchor,
                          verb = verb_override):
            if user.getGrade() < self.grade_min or \
                   user.getGrade() > self.grade_max:
                return 'You are not in the requested grade range for this class.'

        # student has no classes...no conflict there.
        if user.getEnrolledClasses().count() == 0:
            return False

        if user.isEnrolledInClass(self):
            return 'You are already signed up for this class!'
        
        # check to see if there's a conflict:
        for cls in user.getEnrolledClasses().filter(parent_program = self.parent_program):
            for time in cls.meeting_times.all():
                if self.meeting_times.filter(id = time.id).count() > 0:
                    return 'Conflicts with your schedule!'

        # this use *can* add this class!
        return False

        
    def makeTeacher(self, user):
        v = GetNode('V/Flags/Registration/Teacher')
        if UserBit.objects.filter(user = user,
                      qsc = self.anchor,
                      verb = v).count() > 0:
            return True
        
        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)
        ub.save()
        return True

    def removeTeacher(self, user):
        v = GetNode('V/Flags/Registration/Teacher')
        for userbit in UserBit.objects.filter(user = user,
                              qsc = self.anchor,
                              verb = v):
            userbit.delete()


        return True

    def subscribe(self, user):
        v = GetNode('V/Subscribe')
        if UserBit.objects.filter(user = user,
                      qsc = self.anchor,
                      verb = v).count() > 0:
            return False

        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)


        return True
    
    def makeAdmin(self, user, endtime = None):
        v = GetNode('V/Administer/Edit')
        if UserBit.objects.filter(user = user,
                      qsc = self.anchor,
                      verb = v).count() > 0:
            return True

        ub, created = UserBit.objects.get_or_create(user = user,
                                qsc = self.anchor,
                                verb = v)


        return True        


    def removeAdmin(self, user):
        v = GetNode('V/Administer/Edit')
        for userbit in UserBit.objects.filter(user = user,
                              qsc = self.anchor,
                              verb = v):
            userbit.delete()

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

    def students(self):
        cache_id = 'ClassStudents__'+str(self.id)

        retVal = cache.get(cache_id)

        if retVal is not None:
            return retVal

        from esp.users.models import ESPUser
        v = GetNode( 'V/Flags/Registration/Preliminary' )
        students = [ ESPUser(x.user) for x in UserBit.bits_get_users( self.anchor, v ) ]

        students.sort()
        
        cache.set(cache_id, students, self.cache_time())

        return students
    

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

    def friendly_times(self):
        """ will return friendly times for the class """
        cache_id = 'Class__' + str(self.id)

        retVal = cache.get(cache_id)

        if retVal is not None and type(retVal) == dict and retVal.has_key('friendly_times'):
            return retVal['friendly_times']


        if type(retVal) != dict:
            retVal = {}
            
        txtTimes = []
        eventList = []
        for timeanchor in self.meeting_times.all():
            events = Event.objects.filter(anchor=timeanchor)
            if len(events) != 1:
                txtTimes.append(timeanchor.friendly_name)
            else:
                eventList.append(events[0])

        txtTimes += [ event.pretty_time() for event
                  in Event.collapse(eventList) ]

        retVal['friendly_times'] = txtTimes

        cache.set(cache_id, retVal, self.cache_time())

        return txtTimes
            

    def update_cache_students(self):
        from esp.program.templatetags.class_render import cache_key_func
        cache.delete(cache_key_func(self))
        cache.delete('ClassStudents__'+str(self.id))


    def update_cache(self):
        from esp.program.templatetags.class_render import cache_key_func
        cache.delete(cache_key_func(self))
        
        foo = self.teachers(use_cache = False)
        cache.delete('Class__'+str(self.id))

    def preregister_student(self, user, overridefull=False):

        
        prereg_verb = GetNode( 'V/Flags/Registration/Preliminary' )
        
        #    First, delete preregistration bits for other classes at the same time.
        #other_bits = UserBit.objects.filter(user=user, verb=prereg_verb)
        #for b in other_bits:
        #class_qset = Class.objects.filter(anchor=b.qsc, event_template = self.event_template)
        #if class_qset.count() > 0:
        #        b.delete()
                
        if overridefull or not self.isFull():
            #    Then, create the userbit denoting preregistration for this class.
            prereg = UserBit()
            prereg.user = user
            prereg.qsc = self.anchor
            prereg.verb = prereg_verb
            prereg.save()

            self.update_cache_students()


            
            return True
        else:
            #    Pre-registration failed because the class is full.
            return False

    def pageExists(self):
        from esp.qsd.models import QuasiStaticData
        return self.anchor.quasistaticdata_set.filter(name='learn:index').count() > 0

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
        self.status = -10
        self.save()

            
    def docs_summary(self):
        """ Return the first three documents associated with a class, for previewing """
        return self.anchor.media_set.all()[:3]        
            
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



class ClassRoomAssignment(models.Model):
    """ This associates a class, with a room, with a timeblock
        This will prevent problems with classes that have to move """
    room     = AjaxForeignKey(DataTree, related_name="room")
    timeslot = AjaxForeignKey(DataTree, related_name="timeslot")
    unique_together = (('room','timeslot'),)
    
    cls      = models.ForeignKey(Class)
    
class BusSchedule(models.Model):
    """ A scheduled bus journey associated with a program """
    program = models.ForeignKey(Program)
    src_dst = models.CharField(maxlength=128)
    departs = models.DateTimeField()
    arrives = models.DateTimeField()

    class Admin:
        pass


    
class TeacherParticipationProfile(models.Model):
    """ Profile properties associated with a teacher in a program """
    teacher = AjaxForeignKey(User)
    program = models.ForeignKey(Program)
    unique_together = (('teacher', 'program'),)
    bus_schedule = models.ManyToManyField(BusSchedule)
    can_help = models.BooleanField()

    def __str__(self):
        return 'Profile for ' + str(self.teacher) + ' in ' + str(self.program)

    class Admin:
        pass
    

class SATPrepRegInfo(models.Model):
    """ SATPrep Registration Info """
    old_math_score = models.IntegerField(blank=True, null=True)
    old_verb_score = models.IntegerField(blank=True, null=True)
    old_writ_score = models.IntegerField(blank=True, null=True)
    diag_math_score = models.IntegerField(blank=True, null=True)
    diag_verb_score = models.IntegerField(blank=True, null=True)
    diag_writ_score = models.IntegerField(blank=True, null=True)
    prac_math_score = models.IntegerField(blank=True, null=True)
    prac_verb_score = models.IntegerField(blank=True, null=True)
    prac_writ_score = models.IntegerField(blank=True, null=True)    
    heard_by = models.CharField(maxlength=128, blank=True, null=True)
    user = AjaxForeignKey(User)
    program = models.ForeignKey(Program)

    def __str__(self):
        return 'SATPrep regisration info for ' +str(self.user) + ' in '+str(self.program)
    def updateForm(self, new_data):
        for i in self.__dict__.keys():
            if i != 'user_id' and i != 'id' and i != 'program_id':
                new_data[i] = self.__dict__[i]
        return new_data

    
    def addOrUpdate(self, new_data, curUser, program):
        for i in self.__dict__.keys():
            if i != 'user_id' and i != 'id' and i != 'program_id' and new_data.has_key(i):
                self.__dict__[i] = new_data[i]
        self.save()

    @staticmethod
    def getLastForProgram(user, program):
        satPrepList = SATPrepRegInfo.objects.filter(user=user,program=program).order_by('-id')
        if len(satPrepList) < 1:
            satPrep = SATPrepRegInfo()
            satPrep.user = user
            satPrep.program = program
        else:
            satPrep = satPrepList[0]
        return satPrep
    class Admin:
        pass


class RegistrationProfile(models.Model):
    """ A student registration form """
    user = AjaxForeignKey(User)
    program = models.ForeignKey(Program)
    contact_user = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_user')
    contact_guardian = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_guardian')
    contact_emergency = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_emergency')
    student_info = models.ForeignKey(StudentInfo, blank=True, null=True, related_name='as_student')
    teacher_info = models.ForeignKey(TeacherInfo, blank=True, null=True, related_name='as_teacher')
    guardian_info = models.ForeignKey(GuardianInfo, blank=True, null=True, related_name='as_guardian')
    educator_info = models.ForeignKey(EducatorInfo, blank=True, null=True, related_name='as_educator')
    last_ts = models.DateTimeField(default=datetime.now())
    emailverifycode = models.TextField(blank=True, null=True)
    email_verified  = models.BooleanField(default=False, blank=True, null = True)

    @staticmethod
    def getLastProfile(user):
        regProfList = RegistrationProfile.objects.filter(user__exact=user).order_by('-last_ts','-id')
        if len(regProfList) < 1:
            regProf = RegistrationProfile()
            regProf.user = user
        else:
            regProf = regProfList[0]
        return regProf

    def save(self):
        """ update the timestamp """
        self.last_ts = datetime.now()
        super(RegistrationProfile, self).save()
        
    @staticmethod
    def getLastForProgram(user, program):
        regProfList = RegistrationProfile.objects.filter(user__exact=user,program__exact=program).order_by('-last_ts','-id')
        if len(regProfList) < 1:
            regProf = RegistrationProfile()
            regProf.user = user
            regProf.program = program
        else:
            regProf = regProfList[0]
        return regProf
            
    def __str__(self):
        if self.program is None:
            return '<Registration for '+str(self.user)+'>'
        if self.user is not None:
            return '<Registration for ' + str(self.user) + ' in ' + str(self.program) + '>'


    def updateForm(self, form_data, specificInfo = None):
        if self.student_info is not None and (specificInfo is None or specificInfo == 'student'):
            form_data = self.student_info.updateForm(form_data)
        if self.teacher_info is not None and (specificInfo is None or specificInfo == 'teacher'):
            form_data = self.teacher_info.updateForm(form_data)
        if self.guardian_info is not None and (specificInfo is None or specificInfo == 'guardian'):
            form_data = self.guardian_info.updateForm(form_data)
        if self.educator_info is not None and (specificInfo is None or specificInfo == 'educator'):
            form_data = self.educator_info.updateForm(form_data)
        if self.contact_user is not None:
            form_data = self.contact_user.updateForm(form_data)
        if self.contact_guardian is not None:
            form_data = self.contact_guardian.updateForm(form_data, 'guard_')
        if self.contact_emergency is not None:
            form_data = self.contact_emergency.updateForm(form_data, 'emerg_')
        return form_data
    
    def preregistered_classes(self):
        v = GetNode( 'V/Flags/Registration/Preliminary' )
        return UserBit.find_by_anchor_perms(Class, self.user, v, self.program.anchor.tree_decode(['Classes']))
    
    def registered_classes(self):
        v = GetNode( 'V/Flags/Registration/Confirmed' )
        return UserBit.find_by_anchor_perms(Class, self.user, v, self.program.anchor.tree_decode(['Classes']))

    class Admin:
        pass

class TeacherBio(models.Model):
    """ This is the biography of a teacher."""

    program = models.ForeignKey(Program)
    user    = AjaxForeignKey(User)
    bio     = models.TextField(blank=True, null=True)
    slugbio = models.CharField(maxlength=50, blank=True, null=True)
    picture = models.ImageField(height_field = 'picture_height', width_field = 'picture_width', upload_to = "bio_pictures/%y_%m/",blank=True, null=True)
    picture_height = models.IntegerField(blank=True, null=True)
    picture_width  = models.IntegerField(blank=True, null=True)
    last_ts = models.DateTimeField(auto_now = True)    

    class Admin:
        pass

    @staticmethod
    def getLastBio(user):
        bios = TeacherBio.objects.filter(user__exact=user).order_by('-last_ts','-id')
        if len(bios) < 1:
            lastBio = TeacherBio()
            lastBio.user = user
        else:
            lastBio = bios[0]
        return lastBio

    def save(self):
        """ update the timestamp """
        self.last_ts = datetime.now()
        if self.program_id is None:
            try:
                self.program = Program.objects.get(id = 4)
            except:
                raise ESPError(), 'Error: There needs to exist an administrive program with id of 4.'

        super(TeacherBio, self).save()

    def url(self):
        from esp.users.models import ESPUser    
        return '/teach/teachers/%s/%s%s/bio.html' % \
               (self.user.last_name, self.user.first_name, ESPUser(self.user).getUserNum())



    def edit_url(self):
        from esp.users.models import ESPUser    
        return '/teach/teachers/%s/%s%s/bio.edit.html' % \
               (self.user.last_name, self.user.first_name, ESPUser(self.user).getUserNum())

    @staticmethod
    def getLastForProgram(user, program):
        bios = TeacherBio.objects.filter(user__exact=user, program__exact=program).order_by('-last_ts','-id')

        if bios.count() < 1:
            lastBio         = TeacherBio()
            lastBio.user    = user
            lastBio.program = program
        else:
            lastBio = bios[0]
        return lastBio

class FinancialAidRequest(models.Model):
    """
    Student financial Aid Request
    """

    program = models.ForeignKey(Program, editable = False)
    user    = AjaxForeignKey(User, editable = False)

    approved = models.DateTimeField(blank=True, null=True, editable = False)

    reduced_lunch = models.BooleanField(verbose_name = 'Do you receive free/reduced lunch at school?', null=True, blank=True)

    household_income = models.CharField(verbose_name = 'Approximately what is your household income (round do the nearest $10000)?', null=True, blank=True,
                        maxlength=12)

    extra_explaination = models.TextField(verbose_name = 'Please describe in detail your financial situation this summer.', null=True, blank=True)

    student_prepare = models.BooleanField(verbose_name = 'Did anyone besides the student fill out any portions of this form?', blank=True,null=True)

    done = models.BooleanField(default = False, editable = False)


class JunctionStudentApp(models.Model):
    """
    Student applications for Junction.
    """

    

    program = models.ForeignKey(Program, editable = False)
    user    = AjaxForeignKey(User, editable = False)
    class_prep = models.TextField(verbose_name = 'Your School Preperation',
                      help_text = "Please describe your high school preperation. List the classes you've taken thus far.",
                      blank=True,
                      null=True)
    
    ideal_summer = models.TextField(verbose_name = 'My Ideal Summer...',
                    help_text = 'Please write a short essay describing what your ideal summer would be.',
                                    blank=True,null=True)

    difficulty = models.TextField(verbose_name='A difficult triumph',
                      help_text = 'Describe an experience where you had great difficulty in accomplishing something, whether or not it was a success.',
                      blank=True,
                      null=True)

    classes = models.TextField(verbose_name='Please describe your understanding of the classes you chose and why you want to take them.',
                      blank=True,
                      null=True)

    done = models.BooleanField(default=False,editable = False)
    teacher_score = models.PositiveIntegerField(editable=False,null=True,blank=True)
    director_score = models.PositiveIntegerField(editable=False,null=True,blank=True)
    rejected       = models.BooleanField(default=False,editable=False)
    

class JunctionAppReview(models.Model):
    cls = models.ForeignKey(Class)
    junctionapp = models.ForeignKey(JunctionStudentApp)
    student     = models.ForeignKey(User)
    score = models.IntegerField(blank=True,null=True)
    create_ts = models.DateTimeField(default = datetime.now,
                                     editable = False)

    def __str__(self):
        return "Review for %s in class %s" % (self.cls, self.student)

    class Admin:
        pass

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
        ordering = ('-program','seq',)
