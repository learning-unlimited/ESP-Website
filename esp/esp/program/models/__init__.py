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
import copy
import random

from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.cal.models import Event
from esp.datatree.models import *
from esp.users.models import UserBit, ContactInfo, StudentInfo, TeacherInfo, EducatorInfo, GuardianInfo, ESPUser
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Q
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError, AjaxError
from esp.cache import cache_function

#   A function to lazily import models that is occasionally needed for cache dependencies.
def get_model(module_name, model_name):
    parent_module_name = '.'.join(module_name.split('.')[:-1])
    module = __import__(module_name, (), (), parent_module_name)
    try:
        module_class = getattr(module, model_name)
        if issubclass(module_class, models.Model):
            return module_class
    except:
        pass
    return None

# Create your models here.
class ProgramModule(models.Model):
    """ Program Modules for a Program """

    # Title for the link displayed for this Program Module in the Programs form
    link_title = models.CharField(max_length=64, blank=True, null=True)

    # Human-readable name for the Program Module
    admin_title = models.CharField(max_length=128)

    # Main view function associated with this Program Module
    #   Not all program modules have main calls!
    main_call  = models.CharField(max_length=32, blank=True, null=True)

    # One of teach/learn/etc.; What is this module typically used for?
    module_type = models.CharField(max_length=32)

    # self.__name__, stored neatly in the database
    handler    = models.CharField(max_length=32)

    # Sequence orderer.  When ProgramModules are listed on a page, order them
    # from smallest to largest 'seq' value
    seq = models.IntegerField()

    # Secondary view functions associated with this ProgramModule
    aux_calls = models.CharField(max_length=1024, blank=True, null=True)

    # Summary view functions, that summarize data for all instances of this ProgramModule
    summary_calls = models.CharField(max_length=512, blank=True, null=True)

    # Must the user supply this ProgramModule with data in order to complete program registration?
    required = models.BooleanField()

    class Meta:
        app_label = 'program'
        db_table = 'program_programmodule'

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

        def __unicode__(self):
            return self.msg
    
    def __unicode__(self):
        return 'Program Module: %s' % self.admin_title
    
    
class ArchiveClass(models.Model):
    """ Old classes throughout the years """
    program = models.CharField(max_length=256)
    year = models.CharField(max_length=4)
    date = models.CharField(max_length=128)
    category = models.CharField(max_length=16)
    teacher = models.CharField(max_length=1024)
    title = models.CharField(max_length=1024)
    description = models.TextField()
    teacher_ids = models.CharField(max_length=256, blank=True, null=True)
    student_ids = models.TextField()
    original_id = models.IntegerField(blank=True, null=True)
    
    num_old_students = models.IntegerField(default=0)

    class Meta:
        app_label = 'program'
        db_table = 'program_archiveclass'
        verbose_name_plural = 'archive classes'

    #def __unicode__(self):
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
        if len(self.date) > 1:
            year_display = self.year + ' (%s)' % self.date
        else:
            year_display = self.year
            
        return ({'label': 'Teacher', 'value': self.teacher},
            {'label': 'Year', 'value': year_display},
            {'label': 'Program', 'value': self.program},
            {'label': 'Category', 'value': self.category})
    
    def content(self):
        return self.description

    def __unicode__(self):
        from django.template import loader, Context
        t = loader.get_template('models/ArchiveClass.html')
        return t.render(Context({'class': self}, autoescape=True))

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
        useridlist = [int(x) for x in self.student_ids.strip('|').split('|')]
        return ESPUser.objects.filter(id__in = useridlist)
    
    def teachers(self):
        from esp.users.models import ESPUser
        useridlist = [int(x) for x in self.teacher_ids.strip('|').split('|')]
        return User.objects.filter(id__in = useridlist)
    
    @staticmethod
    def getForUser(user):
        """ Get a list of archive classes for a specific user. """
        from django.db.models.query import Q
        Q_ClassTeacher = Q(teacher__icontains = (user.first_name + ' ' + user.last_name)) |\
               Q(teacher_ids__icontains = ('|%s|' % user.id))
        Q_ClassStudent = Q(student_ids__icontains = ('|%s|' % user.id))
        #   We want to only show archive classes for teachers.  At least for now.
        Q_Class = Q_ClassTeacher #  | Q_ClassStudent
        return ArchiveClass.objects.filter(Q_Class).order_by('-year','-date','title')

def _get_type_url(type):
    def _really_get_type_url(self):
        if hasattr(self, '_type_url'):
            if type in self._type_url:
                return self._type_url[type]
        else:
            self._type_url = {}

        self._type_url[type] = '/%s/%s/' % (type, '/'.join(self.anchor.tree_encode()[-2:]))

        return self._type_url[type]

    return _really_get_type_url
        
    

    
class Program(models.Model):
    """ An ESP Program, such as HSSP Summer 2006, Splash Fall 2006, Delve 2005, etc. """
    
    #from esp.program.models.class_ import ClassCategories
    
    anchor = AjaxForeignKey(DataTree) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    director_email = models.EmailField()
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    program_size_max = models.IntegerField(null=True)
    program_allow_waitlist = models.BooleanField(default=False)
    program_modules = models.ManyToManyField(ProgramModule)
    class_categories = models.ManyToManyField('ClassCategories')
    
    class Meta:
        app_label = 'program'
        db_table = 'program_program'

    @cache_function
    def checkitems_all_cached(self):
        """  The main Manage page requests checkitems.all() O(n) times in
        the number of classes in the program.  Minimize the number of these
        calls that actually hit the db. """
        return self.checkitems.all()
    checkitems_all_cached.depend_on_row(lambda:ProgramCheckItem, lambda item: {'self': item.program})

    get_teach_url = _get_type_url("teach")
    get_learn_url = _get_type_url("learn")
    get_manage_url = _get_type_url("manage")
    get_onsite_url = _get_type_url("onsite")

    def save(self, *args, **kwargs):
        
        retVal = super(Program, self).save(*args, **kwargs)
        
        return retVal

    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[-2:])
    
    def __unicode__(self):
        return self.niceName()

    def parent(self):
        return self.anchor.parent

    def niceName(self):
        if not hasattr(self, "_nice_name"):
            # Separate this so that in-memory and memcache are used in the right order
            self._nice_name = self._niceName_memcache()
        return self._nice_name

    @cache_function
    def _niceName_memcache(self):
        return str(self.anchor.parent.friendly_name) + ' ' + str(self.anchor.friendly_name)
    # this stuff never really changes

    def niceSubName(self):
        return self.anchor.name.replace('_', ' ')

    def getUrlBase(self):
        """ gets the base url of this class """
        return self.url() # This makes looking up subprograms by name work; I've left it so that it can be undone without too much effort
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
        from esp.users.models import ESPUser
        
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
            if tmpdict is not None:
                desc.update(tmpdict)

        for k, v in desc.items():
            lists[k]['description'] = v
        usertypes = ['Student', 'Teacher', 'Guardian', 'Educator']

        

        for usertype in usertypes:
            lists['all_'+usertype.lower()+'s'] = {'description':
                                   usertype+'s in all of ESP',
                                   'list' : ESPUser.getAllOfType(usertype)}
        # Filtering by students is a really bad idea
        students_Q = lists['all_students']['list']
        # We can restore this one later if someone really needs it. As it is, I wouldn't mind killing
        # lists['all_former_students'] as well.
        del lists['all_students']
        yog_12 = ESPUser.YOGFromGrade(12)
        # This technically has a bug because of copy-on-write, but the other code has it too, and
        # our copy-on-write system isn't good enough yet to make checking duplicates feasible
        lists['all_current_students'] = {'description': 'Current students in all of ESP',
                'list': students_Q & Q(registrationprofile__student_info__graduation_year__lte = yog_12)}
        lists['all_former_students'] = {'description': 'Former students in all of ESP',
                'list': students_Q & Q(registrationprofile__student_info__graduation_year__gt = yog_12)}

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

    def isFull(self, use_cache=True):
        """ Can this program accept any more students? """
        CACHE_KEY = "PROGRAM__ISFULL_%s" % self.id
        CACHE_DURATION = 10

        if use_cache:
            isfull = cache.get(CACHE_KEY)
            if isfull != None:
                return isfull

        # Some programs don't have caps; this is represented with program_size_max in [ 0, None ]
        if self.program_size_max is None or self.program_size_max == 0:
            return False

        students_dict = self.students(QObjects = True)
        if students_dict.has_key('classreg'):
            students_count = User.objects.filter(students_dict['classreg']).distinct().count()
        else:
            students_count = User.objects.filter(userbit__qsc=self.anchor['Confirmation']).distinct().count()
#            students_count = 0
#            for c in self.classes():
#                students_count += c.num_students(use_cache=True)

        isfull = ( students_count >= self.program_size_max )

        if use_cache:
            cache.set(CACHE_KEY, isfull, CACHE_DURATION)

        return isfull
    
    def classes_node(self):
        return DataTree.objects.get(parent = self.anchor, name = 'Classes')

    def isConfirmed(self, espuser):
        v = GetNode('V/Flags/Public')
        userbits = UserBit.objects.filter(verb = v, user = espuser,
                         qsc = self.anchor.tree_create(['Confirmation']))

        userbits = userbits.filter(enddate__gte=datetime.now())

        if len(userbits) < 1:
            return False
        
        return True
    
    """ These functions have been rewritten.  To avoid confusion, I've changed "ClassRooms" to
    "Classrooms."  So, if you try to call the old functions (which have no point anymore), then 
    you'll get an error and you'll notice that you need to change the call and its associated
    code.               -Michael P
    
    """
    def getClassrooms(self, timeslot=None):
        #   Returns the resources themselves.  See the function below for grouped-by-room.
        from esp.resources.models import ResourceType
        
        if timeslot is not None:
            return self.getResources().filter(event=timeslot, res_type=ResourceType.get_or_create('Classroom'))
        else:
            return self.getResources().filter(res_type=ResourceType.get_or_create('Classroom')).order_by('event')
    
    def getAvailableClassrooms(self, timeslot):
        #   Filters down classrooms to those that are not taken.
        return filter(lambda x: x.is_available(), self.getClassrooms(timeslot))
    
    def collapsed_dict(self, resources):
        result = {}
        for c in resources:
            if c.name not in result:
                #   Make a dictionary with some helper variables for each resource.
                result[c.name] = c
                result[c.name].timeslots = [c.event]

                result[c.name].furnishings = c.associated_resources()
                result[c.name].sequence = c.schedule_sequence(self)
                result[c.name].prog_available_times = c.available_times(self.anchor)
            else:
                result[c.name].timeslots.append(c.event)
            
        for c in result:
            result[c].timegroup = Event.collapse(result[c].timeslots)
        
        return result
    
    def classroom_group_key(self):
        return 'program__groupedclassrooms:%d' % self.id
    
    def clear_classroom_cache(self):
        from django.core.cache import cache
        
        cache_key = self.classroom_group_key()
        cache.delete(cache_key)
    
    def groupedClassrooms(self):
        from django.core.cache import cache
        
        cache_key = self.classroom_group_key()
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        classrooms = self.getClassrooms()
        
        result = self.collapsed_dict(list(classrooms))
        key_list = result.keys()
        key_list.sort()
        #   Turn this into a list instead of a dictionary.
        ans = [result[key] for key in key_list]
        cache.set(cache_key, ans)
        return ans
        
    def addClassroom(self, classroom_form):
        from esp.program.modules.forms.resources import ClassroomForm
        
        #   Parse classroom form to create classroom and associated resources, group them,
        #   and save them.
        assert False, 'todo'
        
    def classes(self):
        return ClassSubject.objects.filter(parent_program = self).order_by('id')        

    def class_ids_implied(self, use_cache=True):
        """ Returns the class ids implied by classes in this program. Returns [-1] for none so the cache doesn't keep getting hit. """
        cache_key = 'PROGRAM__CLASS_IDS_IMPLIED__%s' % self.id
        retVal = cache.get(cache_key)
        if retVal and use_cache:
            return retVal
        retVal = set([])
        for c in self.classes():
            for imp in c.classimplication_set.all():
                retVal = retVal.union(imp.member_id_ints)
        if len(retVal) < 1:
            retVal = [-1]
        retVal = list(retVal)
        cache.set(cache_key, retVal, 9999)
        return retVal

    def sections(self, use_cache=True):
        return ClassSection.objects.filter(parent_class__parent_program=self).distinct().order_by('id').select_related('parent_class')

    def getTimeSlots(self, exclude_types=['Compulsory']):
        """ Get the time slots for a program. 
            A flag, exclude_types, allows you to restrict which types of timeslots
            are grabbed.  The default excludes 'compulsory' events, which are
            not intended to be used for classes (they're for lunch, photos, etc.)
        """
        return Event.objects.filter(anchor=self.anchor).exclude(event_type__description__in=exclude_types).order_by('start')

    def total_duration(self):
        """ Returns the total length of the events in this program, as a timedelta object. """
        ts_list = Event.collapse(list(self.getTimeSlots()), tol=timedelta(minutes=15))
        time_sum = timedelta()
        for t in ts_list:
            time_sum = time_sum + (t.end - t.start)
        return time_sum

    def date_range(self):
        dates = self.getTimeSlots()
        d1 = min(dates).start
        d2 = max(dates).end
        if d1.year == d2.year:
            if d1.month == d2.month:
                return '%s - %s' % (d1.strftime('%b. %d'), d2.strftime('%d, %Y'))
            else:
                return '%s - %s' % (d1.strftime('%b. %d'), d2.strftime('%b. %d, %Y'))
        else:
            return '%s - %s' % (d1.strftime('%b. %d, %Y'), d2.strftime('%b. %d, %Y'))

    def getResourceTypes(self):
        #   Show all resources pertaining to the program that aren't these two hidden ones.
        from esp.resources.models import ResourceType
        exclude_types = [ResourceType.get_or_create('Classroom')]
        
        Q_filters = Q(program=self) | Q(program__isnull=True)
        
        #   Inherit resource types from parent programs.
        parent_program = self.getParentProgram()
        if parent_program is not None:
            Q_parent = Q(id__in=[rt.id for rt in parent_program.getResourceTypes()])
            Q_filters = Q_filters | Q_parent
        
        return ResourceType.objects.filter(Q_filters).exclude(id__in=[t.id for t in exclude_types])

    def getResources(self):
        from esp.resources.models import Resource
        return Resource.objects.filter(event__anchor=self.anchor)
    
    def getFloatingResources(self, timeslot=None, queryset=False):
        from esp.resources.models import ResourceType
        #   Don't include classrooms and teachers in the floating resources.
        exclude_types = [ResourceType.get_or_create('Classroom')]
        
        if timeslot is not None:
            res_list = self.getResources().filter(event=timeslot, is_unique=True).exclude(res_type__in=exclude_types)
        else:
            res_list = self.getResources().filter(is_unique=True).exclude(res_type__in=exclude_types)
            
        if queryset:
            return res_list
        else:
            result = self.collapsed_dict(res_list)
            return [result[c] for c in result]

    def getAvailableResources(self, timeslot):
        #   Filters down the floating resources to those that are not taken.
        return filter(lambda x: x.is_available(), self.getFloatingResources(timeslot))

    def getDurations(self, round=False):
        """ Find all contiguous time blocks and provide a list of duration options. """
        from esp.program.modules.module_ext import ClassRegModuleInfo
        from decimal import Decimal
        
        times = Event.group_contiguous(list(self.getTimeSlots()))
        info_list = ClassRegModuleInfo.objects.filter(module__program=self)
        if info_list.count() == 1 and type(info_list[0].class_max_duration) == int:
            max_seconds = info_list[0].class_max_duration * 60
        else:
            max_seconds = None

        durationDict = {}
        
        #   I hope this isn't too terribly slow... not bothering with a faster way
        for t_list in times:
            n = len(t_list)
            for i in range(0, n):
                for j in range(i, n):
                    time_option = t_list[j].end - t_list[i].start
                    durationSeconds = time_option.seconds
                    #   If desired, round up to the nearest 15 minutes
                    if round:
                        rounded_seconds = int(durationSeconds / 900.0 + 1.0) * 900
                    else:
                        rounded_seconds = durationSeconds
                    if (max_seconds is None) or (durationSeconds <= max_seconds):
                        durationDict[Decimal(durationSeconds) / 3600] = \
                                        str(rounded_seconds / 3600) + ':' + \
                                        str((rounded_seconds / 60) % 60).rjust(2,'0')
            
        durationList = durationDict.items()

        return durationList

    def getSurveys(self):
        from esp.survey.models import Survey
        return Survey.objects.filter(anchor=self.anchor)
    
    def getSubprograms(self):
        if not self.anchor.has_key('Subprograms'):
            return Program.objects.filter(id=-1)
        return Program.objects.filter(anchor__parent__in=self.anchor['Subprograms'].children())
    
    def getParentProgram(self):
        #   Ridiculous syntax is actually correct for our subprograms scheme.
        pl = []
        if self.anchor.parent.parent.name == 'Subprograms':
            pl = Program.objects.filter(anchor=self.anchor.parent.parent.parent)
        if len(pl) == 1:
            return pl[0]
        else:
            return None
        
    def getLineItemTypes(self, user=None, required=True):
        from esp.accounting_core.models import LineItemType, Balance
        
        if required:
            li_types = list(LineItemType.objects.filter(anchor=GetNode(self.anchor.get_uri()+'/LineItemTypes/Required')))
        else:
            li_types = list(LineItemType.objects.filter(anchor__parent=GetNode(self.anchor.get_uri()+'/LineItemTypes/Optional')))
        
        #   OK, nevermind... Add in *parent program* line items that have not been paid for.
        parent_li_types = []
        cur_anchor = self.anchor
        parent_prog = self.getParentProgram()
        #   Check if there's a parent program and the student is registered for it.
        if (parent_prog is not None) and (user is not None) and (User.objects.filter(parent_prog.students(QObjects=True)['classreg']).filter(id=user.id).count() != 0):
            cur_anchor = parent_prog.anchor
            parent_li_types += list(LineItemType.objects.filter(anchor=GetNode(parent_prog.anchor.get_uri()+'/LineItemTypes/Required')))
        for li in parent_li_types:
            li.bal = Balance.get_current_balance(user, li)
            if Balance.get_current_balance(user, li)[0] == 0:
                li_types.append(li)
                
        return li_types
    
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

    @cache_function
    def getModuleExtension(self, ext_name_or_cls, module_id=None):
        """ Get the specified extension (e.g. ClassRegModuleInfo) for a program.
        This avoids actually looking up the program module first. """

        if not hasattr(self, "_moduleExtensions"):
            self._moduleExtensions = {}
        elif (ext_name_or_cls, module_id) in self._moduleExtensions:
            return self._moduleExtensions[(ext_name_or_cls, module_id)]
        
        ext_cls = None
        if type(ext_name_or_cls) == str or type(ext_name_or_cls) == unicode:
            mod = __import__('esp.program.modules.module_ext', (), (), ext_name_or_cls)
            ext_cls = getattr(mod, ext_name_or_cls)
        else:
            ext_cls = ext_name_or_cls
            
        if module_id:
            try:
                extension = ext_cls.objects.filter(module__id=module_id)[0]
            except:
                extension = ext_cls()
                extension.module_id = module_id
                extension.save()
        else:
            try:
                extension = ext_cls.objects.filter(module__program__id=self.id)[0]
            except:
                extension = None

        self._moduleExtensions[(ext_name_or_cls, module_id)] = extension
                
        return extension
    #   Depend on all module extensions (kind of ugly, but at least we don't change those too frequently).
    #   Ideally this could be autodetected by importing everything from module_ext first, but I ran into
    #   a circular import problem.   -Michael P
    getModuleExtension.depend_on_model(lambda: get_model('esp.program.modules.module_ext', 'ClassRegModuleInfo'))
    getModuleExtension.depend_on_model(lambda: get_model('esp.program.modules.module_ext', 'StudentClassRegModuleInfo'))
    getModuleExtension.depend_on_model(lambda: get_model('esp.program.modules.module_ext', 'SATPrepAdminModuleInfo'))
    getModuleExtension.depend_on_model(lambda: get_model('esp.program.modules.module_ext', 'CreditCardModuleInfo'))
    getModuleExtension.depend_on_model(lambda: get_model('esp.program.modules.module_ext', 'SATPrepTeacherModuleInfo'))

    def getColor(self):
        if hasattr(self, "_getColor"):
            return self._getColor
        
        cache_key = 'PROGRAM__COLOR_%s' % self.id
        retVal = cache.get(cache_key)
        
        if not retVal:
            mod = self.programmoduleobj_set.filter(module__admin_title='Teacher Signup Classes')
            if mod.count() == 1:
                modinfo = mod[0].classregmoduleinfo_set.all()
                if modinfo.count() == 1:
                    retVal = modinfo[0].color_code
                    if retVal == None:
                        retVal = -1 # store None as -1 because we read None as the absence of a cached value
                    cache.set(cache_key, retVal, 9999)
        if retVal == -1:
            return None

        self._getColor = retVal
        return retVal
    
    def visibleEnrollments(self):
        """
        Returns whether class enrollments should show up in the catalog.
        This originally returned true if class registration was fully open.
        Now it's just a checkbox in the StudentClassRegModuleInfo.
        """
        options = self.getModuleExtension('StudentClassRegModuleInfo')
        return options.visible_enrollments
    
    def archive(self):
        archived_classes = []
        #   I think we should delete resources and user bits, but I'm afraid to.
        #   So, just archive all of the classes.
        for c in self.classes():
            archived_classes.append(c.archive())
            print 'Archived: %s' % c.title()
        
        return archived_classes
    
    @staticmethod
    def find_by_perms(user, verb):
        """ Fetch a list of relevant programs for a given user and verb """
        return UserBit.find_by_anchor_perms(Program,user,verb)

    @classmethod
    def by_prog_inst(cls, program, instance):
        CACHE_KEY = "PROGRAM__BY_PROG_INST__%s__%s" % (program, instance)
        prog_inst = cache.get(CACHE_KEY)
        if prog_inst:
            return prog_inst
        else:
            prog_inst = Program.objects.select_related().get(anchor__name=instance, anchor__parent__name=program)
            cache.add(CACHE_KEY, prog_inst, timeout=86400)
            return prog_inst

    
class BusSchedule(models.Model):
    """ A scheduled bus journey associated with a program """
    program = models.ForeignKey(Program)
    src_dst = models.CharField(max_length=128)
    departs = models.DateTimeField()
    arrives = models.DateTimeField()

    class Meta:
        app_label = 'program'
        db_table = 'program_busschedule'

    
class TeacherParticipationProfile(models.Model):
    """ Profile properties associated with a teacher in a program """
    teacher = AjaxForeignKey(User)
    program = models.ForeignKey(Program)
    unique_together = (('teacher', 'program'),)
    bus_schedule = models.ManyToManyField(BusSchedule)
    can_help = models.BooleanField()

    class Meta:
        app_label = 'program'
        db_table = 'program_teacherparticipationprofile'

    def __unicode__(self):
        return 'Profile for ' + str(self.teacher) + ' in ' + str(self.program)
    

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
    heard_by = models.CharField(max_length=128, blank=True, null=True)
    user = AjaxForeignKey(User)
    program = models.ForeignKey(Program)

    class Meta:
        app_label = 'program'
        db_table = 'program_satprepreginfo'
        verbose_name = 'SATPrep Registration Info'

    def __unicode__(self):
        return 'SATPrep registration info for ' +str(self.user) + ' in '+str(self.program)
    
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


class RegistrationProfile(models.Model):
    """ A student registration form """
    user = AjaxForeignKey(User)
    program = models.ForeignKey(Program)
    contact_user = AjaxForeignKey(ContactInfo, blank=True, null=True, related_name='as_user')
    contact_guardian = AjaxForeignKey(ContactInfo, blank=True, null=True, related_name='as_guardian')
    contact_emergency = AjaxForeignKey(ContactInfo, blank=True, null=True, related_name='as_emergency')
    student_info = AjaxForeignKey(StudentInfo, blank=True, null=True, related_name='as_student')
    teacher_info = AjaxForeignKey(TeacherInfo, blank=True, null=True, related_name='as_teacher')
    guardian_info = AjaxForeignKey(GuardianInfo, blank=True, null=True, related_name='as_guardian')
    educator_info = AjaxForeignKey(EducatorInfo, blank=True, null=True, related_name='as_educator')
    last_ts = models.DateTimeField(default=datetime.now())
    emailverifycode = models.TextField(blank=True, null=True)
    email_verified  = models.BooleanField(default=False, blank=True)
    text_reminder = models.NullBooleanField()

    class Meta:
        app_label = 'program'
        db_table = 'program_registrationprofile'

    @cache_function
    def getLastProfile(user):
        regProf = None
        
        if isinstance(user.id, int):
            try:
                regProf = RegistrationProfile.objects.filter(user__exact=user).latest('last_ts')
            except:
                pass

        if regProf != None:
            return regProf
        
        regProf = RegistrationProfile()
        regProf.user = user

        return regProf
    getLastProfile.depend_on_row(lambda:RegistrationProfile, lambda profile: {'user': profile.user})
    getLastProfile = staticmethod(getLastProfile) # a bit annoying, but meh

    def confirmStudentReg(self, user):
        """ Confirm the specified user's registration in the program """
        bits = UserBit.objects.filter(user=user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(self.anchor.tree_encode()) + "/Confirmation")).filter(enddate__gte=datetime.now())
        if bits.count() == 0:
            bit = UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))

    def cancelStudentRegConfirmation(self, user):
        """ Cancel the registration confirmation for the specified student """
        raise ESPError(), "Error: You can't cancel a registration confirmation!  Confirmations are final!"
        #for bit in UserBit.objects.filter(user=user, verb=GetNode("V/Flags/Public"), qsc__parent=self.anchor, qsc__name="Confirmation").filter(enddate__gte=datetime.now()):
        #    bit.expire()
        
    def save(self, *args, **kwargs):
        """ update the timestamp and clear getLastProfile cache """
        self.last_ts = datetime.now()
        super(RegistrationProfile, self).save(*args, **kwargs)
        
    @staticmethod
    def getLastForProgram(user, program):
        """ Returns the newest RegistrationProfile attached to this user and this program (or any ancestor of this program). """
        regProfList = RegistrationProfile.objects.filter(user__exact=user,program__exact=program).order_by('-last_ts','-id')[:1]
        if len(regProfList) < 1:
            # Has this user already filled out a profile for the parent program?
            parent_program = program.getParentProgram()
            if parent_program is not None:
                regProf = RegistrationProfile.getLastForProgram(user, parent_program)
                regProf.program = program
                # If they've filled out a profile for the parent program, use a copy of that.
                if regProf.id is not None:
                    regProf.id = None
                    regProf.save()
            else:
                regProf = RegistrationProfile.getLastProfile(user)
                if (datetime.now() - regProf.last_ts).days > 5:
                    regProf = RegistrationProfile()
                    regProf.user = user
                regProf.program = program
        else:
            regProf = regProfList[0]
        return regProf
            
    def __unicode__(self):
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
    
    #   Note: these functions return ClassSections, not ClassSubjects.
    def preregistered_classes(self):
        return ESPUser(self.user).getSections(program=self.program)
    
    def registered_classes(self):
        return ESPUser(self.user).getEnrolledSections(program=self.program)


class TeacherBio(models.Model):
    """ This is the biography of a teacher."""

    program = models.ForeignKey(Program)
    user    = AjaxForeignKey(User)
    bio     = models.TextField(blank=True, null=True)
    slugbio = models.CharField(max_length=50, blank=True, null=True)
    picture = models.ImageField(height_field = 'picture_height', width_field = 'picture_width', upload_to = "uploaded/bio_pictures/%y_%m/",blank=True, null=True)
    picture_height = models.IntegerField(blank=True, null=True)
    picture_width  = models.IntegerField(blank=True, null=True)
    last_ts = models.DateTimeField(auto_now = True)    

    class Meta:
        app_label = 'program'
        db_table = 'program_teacherbio'

    @staticmethod
    def getLastBio(user):
        bios = TeacherBio.objects.filter(user__exact=user).order_by('-last_ts','-id')
        if len(bios) < 1:
            lastBio = TeacherBio()
            lastBio.user = user
        else:
            lastBio = bios[0]
        return lastBio

    def save(self, *args, **kwargs):
        """ update the timestamp """
        self.last_ts = datetime.now()
        if self.program_id is None:
            try:
                self.program = Program.objects.get(anchor = GetNode("Q/Programs/Dummy_Programs/Profile_Storage"))
            except:
                raise ESPError(), 'Error: There needs to exist an administrive program anchored at Q/Programs/Dummy_Programs/Profile_Storage.'

        super(TeacherBio, self).save(*args, **kwargs)

    def url(self):
        return '/teach/teachers/%s/bio.html' % self.user.username



    def edit_url(self):
        return '/teach/teachers/%s/bio.edit.html' % self.user.username

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

    approved = models.DateTimeField(blank=True, null=True)

    reduced_lunch = models.BooleanField(verbose_name = 'Do you receive free/reduced lunch at school?', blank=True, default=False)

    household_income = models.CharField(verbose_name = 'Approximately what is your household income (round to the nearest $10,000)?', null=True, blank=True,
                        max_length=12)

    extra_explaination = models.TextField(verbose_name = 'Please describe in detail your financial situation this year', null=True, blank=True)

    student_prepare = models.BooleanField(verbose_name = 'Did anyone besides the student fill out any portions of this form?', blank=True, default=False)

    done = models.BooleanField(default=False, editable=False)

    reviewed = models.BooleanField(default=False, verbose_name='Reviewed by Directors')

    amount_received = models.IntegerField(blank=True,null=True, verbose_name='Amount granted')
    amount_needed = models.IntegerField(blank=True,null=True, verbose_name='Amount due from student')

    class Meta:
        app_label = 'program'
        db_table = 'program_financialaidrequest'

    def save(self, *args, **kwargs):
        """ If possible, find the student's invoice and update it to reflect the 
        financial aid that has been granted. """
        
        #   By default, the amount received is 0.  If this is the case, don't do
        #   any extra work.
        models.Model.save(self, *args, **kwargs)
        if (not self.amount_received) or (self.amount_received <= 0):
            return
        
        from esp.accounting_docs.models import Document
        from esp.accounting_core.models import LineItemType
        from decimal import Decimal
        
        #   Take the 'root' program for the tree anchors.
        pp = self.program.getParentProgram()
        if pp:
            anchor = pp.anchor
        else:
            anchor = self.program.anchor

        inv = Document.get_invoice(self.user, anchor)
        txn = inv.txn
        funding_node = anchor['Accounts']
       
        #   Find the amount we're charging the student for the program and ensure
        #   that we don't award more financial aid than charges.
        charges = txn.lineitem_set.filter(QTree(anchor__below=anchor), anchor__parent__name='LineItemTypes',)
       
        chg_amt = 0
        for li in charges:
            chg_amt += li.amount
        if self.amount_received > (-chg_amt):
            self.amount_received = -chg_amt
        
        #   Reverse all financial aid awards and add a new line item for this one.
        finaids = txn.lineitem_set.filter(QTree(anchor__below=anchor), anchor__parent__name='Accounts')
        rev_li_type, unused = LineItemType.objects.get_or_create(text='Financial Aid Reversal',anchor=funding_node['FinancialAid'])
        fwd_li_type, unused = LineItemType.objects.get_or_create(text='Financial Aid',anchor=funding_node['FinancialAid'])
        for li in finaids:
            if li.amount != 0:
                txn.add_item(self.user, rev_li_type, amount=-(li.amount))
        txn.add_item(self.user, fwd_li_type, amount=Decimal(str(self.amount_received)))
    
    def __unicode__(self):
        """ Represent this as a string. """
        accepted_verb = GetNode('V/Flags/Registration/Accepted')
        if self.reduced_lunch:
            reducedlunch = "(Free Lunch)"
        else:
            reducedlunch = ''
            
        explanation = self.extra_explaination
        if explanation is None:
            explanation = ''
        elif len(explanation) > 40:
            explanation = explanation[:40] + "..."


        string = "%s (%s@esp.mit.edu) for %s (%s, %s) %s"%\
                 (ESPUser(self.user).name(), self.user.username, self.program.niceName(), self.household_income, explanation, reducedlunch)

        if self.done:
            string = "Finished: [" + string + "]"

        if self.reviewed:
            string += " (REVIEWED)"

        return string
        
""" Functions for scheduling constraints
    I'm sorry that these are in the same __init__.py file;
    whenever I tried moving them to a separate file, 
    Django wouldn't install the models. 
"""
        
def get_subclass_instance(cls, obj):
    for c in cls.__subclasses__():
        #   Try casting the object into each of the subclasses.
        #   If you find an object, return it.
        result = None
        try:
            result = c.objects.get(id=obj.id)
        except:
            pass
        if result:
            return get_subclass_instance(c, result)
    #   If you couldn't find any, return the original object.
    return obj

class BooleanToken(models.Model):
    """ A true/false value or Boolean operation.
        Meant to be extended to more meaningful Boolean functions operating on
        other models, such as:
        - Whether a user is violating a schedule constraint
        - Whether a user is in a particular age range
        - Whether a user has been e-mailed in the last month
        
        Also meant to be combined into logical expressions for queries/tests
        (see BooleanExpression below).
    """
    exp = models.ForeignKey('BooleanExpression', help_text='The Boolean expression that this token belongs to')
    text = models.TextField(help_text='Boolean value, or text needed to compute it', default='', blank=True)
    seq = models.IntegerField(help_text='Location of this token on the expression stack (larger numbers are higher)', default=0)

    def get_expr(self):
        return self.exp.subclass_instance()
    #   Renamed to expr to avoid conflicting with Django SQL evaluator "expression"
    expr = property(get_expr)

    def __unicode__(self):
        return '[%d] %s' % (self.seq, self.text)

    def subclass_instance(self):
        return get_subclass_instance(BooleanToken, self)

    @staticmethod
    def evaluate(stack, *args, **kwargs):
        """ Evaluate a stack of Boolean tokens. 
            Operations (including the basic ones defined below) take their
            arguments off the stack.
        """
        value = None
        stack = list(stack)
        while (value is None) and (len(stack) > 0):
            token = stack.pop().subclass_instance()
            #   print 'Popped token: %s' % token.text
            
            # Handle possibilities for what the token might be:
            if (token.text == '||') or (token.text.lower() == 'or'):
                # - or operator
                (value1, stack) = BooleanToken.evaluate(stack, *args, **kwargs)
                (value2, stack) = BooleanToken.evaluate(stack, *args, **kwargs)
                value = (value1 or value2)
            elif (token.text == '&&') or (token.text.lower() == 'and'):
                # - and operator
                (value1, stack) = BooleanToken.evaluate(stack, *args, **kwargs)
                (value2, stack) = BooleanToken.evaluate(stack, *args, **kwargs)
                value = (value1 and value2)
            elif (token.text == '!') or (token.text == '~') or (token.text.lower() == 'not'):
                # - not operator
                (value1, stack) = BooleanToken.evaluate(stack, *args, **kwargs)
                value = (not value1)
            else:
                # - direct boolean value
                # Pass along arguments
                value = token.boolean_value(*args, **kwargs)
                
        #   print 'Returning value: %s, stack: %s' % (value, [s.text for s in stack])
        return (value, stack)

    """ This function is meant to take extra arguments so subclasses can use additional
        information in order to compute their value (i.e. schedule information) """
    def boolean_value(self, *args, **kwargs):
        if (self.text == '1') or (self.text.lower() == 't') or (self.text.lower() == 'true'):
            return True
        else:
            return False
            
            
class BooleanExpression(models.Model):
    """ A combination of BooleanTokens that can be manipulated and evaluated. 
        Arbitrary arguments can be supplied to the evaluate function in order
        to help subclassed tokens do their thing.
    """
    label = models.CharField(max_length=80, help_text='Description of the expression')

    def __unicode__(self):
        return '(%d tokens) %s' % (self.get_stack().count(), self.label)

    def subclass_instance(self):
        return get_subclass_instance(BooleanExpression, self)

    def get_stack(self):
        return self.booleantoken_set.all().order_by('seq')
        
    def reset(self):
        self.booleantoken_set.all().delete()

    def add_token(self, token_or_value, seq=None, duplicate=True):
        my_stack = self.get_stack()
        if type(token_or_value) == str:
            print 'Adding new token %s to %s' % (token_or_value, unicode(self))
            new_token = BooleanToken(text=token_or_value)
        elif duplicate:
            token_type = type(token_or_value)
            print 'Adding duplicate of token %d, type %s, to %s' % (token_or_value.id, token_type.__name__, unicode(self))
            new_token = token_type()
            #   Copy over fields that don't describe relations
            for item in new_token._meta.fields:
                if not item.__class__.__name__ in ['AutoField', 'OneToOneField']:
                    setattr(new_token, item.name, getattr(token_or_value, item.name))
        else:
            print 'Adding new token %s to %s' % (token_or_value, unicode(self))
            new_token = token_or_value
        if seq is None:
            if my_stack.count() > 0:
                new_token.seq = self.get_stack().order_by('-seq').values('seq')[0]['seq'] + 10
            else:
                new_token.seq = 0
        else:
            new_token.seq = seq
        new_token.exp = self
        new_token.save()
        print 'New token ID: %d' % new_token.id
        return new_token
    
    def evaluate(self, *args, **kwargs):
        stack = self.get_stack()
        (value, post_stack) = BooleanToken.evaluate(stack, *args, **kwargs)
        return value


class ScheduleMap:
    """ The schedule map is a dictionary mapping Event IDs to lists of class sections.
        It can be generated and cached for a user, then modified
        (by adding/removing values) to quickly model the effect of a particular
        schedule change.
    """
    @cache_function
    def __init__(self, user, program):
        if type(user) is not ESPUser:
            user = ESPUser(user)
        self.program = program
        self.user = user
        self.populate()
    __init__.depend_on_row(lambda: UserBit, lambda bit: {'user': bit.user}, lambda bit: bit.verb.get_uri().startswith('V/Flags/Registration'))

    @cache_function
    def populate(self):
        result = {}
        for t in self.program.getTimeSlots():
            result[t.id] = []
        sl = self.user.getEnrolledSections(self.program)
        for s in sl:
            for m in s.meeting_times.all():
                result[m.id].append(s)
        self.map = result
        return self.map
    populate.depend_on_row(lambda: UserBit, lambda bit: {}, lambda bit: bit.verb.get_uri().startswith('V/Flags/Registration'))

    def add_section(self, sec):
        for t in sec.meeting_times.all().values_list('id'):
            self.map[t[0]].append(sec)

    def __marinade__(self):
        import hashlib
        import pickle
        return 'ScheduleMap_%s' % hashlib.md5(pickle.dumps(self)).hexdigest()[:8]
        
    def __unicode__(self):
        return '%s' % self.map

class ScheduleConstraint(models.Model):
    """ A scheduling constraint that can be tested: 
        IF [condition] THEN [requirement]
        
        This constraint requires that [requirement] be true in order
        for [condition] to be true.  Examples:
        - IF [all other blocks are non-lunch] THEN [this block must be lunch]
        - IF [student taking class B] THEN [student took class A beforehand]
        
        The input to this calculation is a ScheduleMap (see above).
        ScheduleConstraint.evaluate([map]) returns:
        - False if the provided [map] would violate the constraint
        - True if the provided [map] would satisfy the constraint
    """
    program = models.ForeignKey(Program)

    condition = models.ForeignKey(BooleanExpression, related_name='condition_constraint')
    requirement = models.ForeignKey(BooleanExpression, related_name='requirement_constraint')
    #   This is a function of one argument, schedule_map, which returns an updated schedule_map.
    on_failure = models.TextField()
    
    def __unicode__(self):
        return '%s: "%s" requires "%s"' % (self.program.niceName(), unicode(self.condition), unicode(self.requirement))
    
    @cache_function
    def evaluate(self, smap, recursive=True):
        self.schedule_map = smap
        cond_state = self.condition.evaluate(map=self.schedule_map.map)
        if cond_state:
            result = self.requirement.evaluate(map=self.schedule_map.map)
            if result:
                return True
            else:
                if recursive:
                    #   Try using the execution hook for arbitrary code... and running again to see if it helped.
                    (fail_result, data) = self.handle_failure()
                    if type(fail_result) == ScheduleMap:
                        self.schedule_map = fail_result
                    #   raise AjaxError('ScheduleConstraint says %s' % data)
                    return self.evaluate(self.schedule_map, recursive=False)
                else:
                    return False
        else:
            return True
    # It's okay to flush the cache if any of the boolean expressions change, since
    # that isn't very frequent.
    evaluate.depend_on_model(lambda: BooleanToken)
    evaluate.depend_on_model(lambda: BooleanExpression)

    def handle_failure(self):
        #   Try the on_failure callback but be very lenient about it (fail silently)
        try:
            func_str = """def _f(schedule_map):
%s""" % ('\n'.join('    %s' % l.rstrip() for l in self.on_failure.strip().split('\n')))
            #   print func_str
            exec func_str
            result = _f(self.schedule_map)
            return result
        except Exception, inst:
            #   raise ESPError(False), 'Schedule constraint handler error: %s' % inst
            pass
        #   If we got nothing from the on_failure function, just provide Nones.
        return (None, None)

class ScheduleTestTimeblock(BooleanToken):
    """ A boolean value that keeps track of a timeblock. 
        This is an abstract base class that doesn't define
        the boolean_value function.
    """
    timeblock = models.ForeignKey(Event, help_text='The timeblock that this schedule test pertains to')

class ScheduleTestOccupied(ScheduleTestTimeblock):
    """ Boolean value testing: Does the schedule contain at least one
        section at the specified time?
    """
    def boolean_value(self, *args, **kwargs):
        timeblock_id = self.timeblock.id
        user_schedule = kwargs['map']
        if timeblock_id in user_schedule:
            if len(user_schedule[timeblock_id]) > 0:
                return True
        return False

class ScheduleTestCategory(ScheduleTestTimeblock):
    """ Boolean value testing: Does the schedule contain at least one section 
        in the specified category at the specified time?
    """
    category = models.ForeignKey('ClassCategories', help_text='The class category that must be selected for this timeblock')
    def boolean_value(self, *args, **kwargs):
        timeblock_id = self.timeblock.id
        user_schedule = kwargs['map']
        if timeblock_id in user_schedule:
            for sec in user_schedule[timeblock_id]:
                if sec.category == self.category:
                    return True
        return False
            
class ScheduleTestSectionList(ScheduleTestTimeblock):
    """ Boolean value testing: Does the schedule contain one of the specified
        sections at the specified time?
    """
    section_ids = models.TextField(help_text='A comma separated list of ClassSection IDs that can be selected for this timeblock')
    def boolean_value(self, *args, **kwargs):
        timeblock_id = self.timeblock.id
        user_schedule = kwargs['map']
        section_id_list = [int(a) for a in self.section_ids.split(',')]
        if timeblock_id in user_schedule:
            for sec in user_schedule[timeblock_id]:
                if sec.id in section_id_list:
                    return True
        return False
        
    @classmethod
    def filter_by_section(cls, section):
        return cls.filter_by_sections([section])

    @classmethod
    def filter_by_sections(cls, sections):
        import operator
        q_list = []
        for section in sections:
            q_list.append(Q(Q(section_ids='%s' % section.id) | Q(section_ids__startswith='%s,' % section.id) | Q(section_ids__contains=',%s,' % section.id) | Q(section_ids__endswith=',%s' % section.id)))

        return cls.objects.filter( reduce(operator.or_, q_list) )
           
def schedule_constraint_test(prog):
    sc = ScheduleConstraint(program=prog)
    return True
    
    
from esp.program.models.class_ import *
from esp.program.models.app_ import *

def install():
    """ Setup for program. """
    from esp.program.dummy_program import init_dummy_program
    init_dummy_program()
