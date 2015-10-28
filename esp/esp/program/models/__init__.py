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

import copy
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta, date
from decimal import Decimal
import random
import simplejson as json

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.localflavor.us.models import PhoneNumberField
from django.core import urlresolvers
from django.core.cache import cache
from django.db import models
from django.db.models import Count
from django.db.models import Q
from django.db.models.query import QuerySet

from esp.cache import cache_function
from esp.cache.key_set import wildcard
from esp.cal.models import Event
from esp.customforms.linkfields import CustomFormsLinkModel
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError, AjaxError
from esp.tagdict.models import Tag
from esp.users.models import ContactInfo, StudentInfo, TeacherInfo, EducatorInfo, GuardianInfo, ESPUser, shirt_sizes, shirt_types, Record
from esp.utils.expirable_model import ExpirableModel
from esp.utils.formats import format_lazy
from esp.qsdmedia.models import Media


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

    #   A module can have an inline template (whose context is filled by prepare())
    #   independently of its main view.
    inline_template = models.CharField(max_length=32, blank=True, null=True)

    # One of teach/learn/etc.; What is this module typically used for?
    module_type = models.CharField(max_length=32)

    # self.__name__, stored neatly in the database
    handler    = models.CharField(max_length=32)

    # Sequence orderer.  When ProgramModules are listed on a page, order them
    # from smallest to largest 'seq' value
    seq = models.IntegerField()
    
    # Must the user supply this ProgramModule with data in order to complete program registration?
    required = models.BooleanField()

    class Meta:
        app_label = 'program'
        db_table = 'program_programmodule'

    def getFriendlyName(self):
        """ Return a human-readable name that identifies this Program Module """
        return self.admin_title

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
            super(ProgramModule.CannotGetClassException, self).__init__(msg)

    def __unicode__(self):
        return u'Program Module: %s' % self.admin_title
    
    
class ArchiveClass(models.Model):
    """ Old classes throughout the years """
    program = models.CharField(max_length=256)
    year = models.CharField(max_length=4)
    date = models.CharField(max_length=128)
    category = models.CharField(max_length=32)
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
        from esp.middleware.threadlocalrequest import AutoRequestContext as Context
        from django.template import loader
        t = loader.get_template('program/archive_class.html')
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
        useridlist = [int(x) for x in self.student_ids.strip('|').split('|')]
        return ESPUser.objects.filter(id__in = useridlist)
    
    def teachers(self):
        useridlist = [int(x) for x in self.teacher_ids.strip('|').split('|')]
        return ESPUser.objects.filter(id__in = useridlist)
    
    @staticmethod
    def getForUser(user):
        """ Get a list of archive classes for a specific user. """
        from django.db.models.query import Q
        Q_ClassTeacher = Q(teacher_ids__icontains = ('|%s|' % user.id))
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

        self._type_url[type] = '/%s/%s/' % (type, self.url)

        return self._type_url[type]

    return _really_get_type_url
    

class Program(models.Model, CustomFormsLinkModel):
    """ An ESP Program, such as HSSP Summer 2006, Splash Fall 2006, Delve 2005, etc. """
    #customforms definitions
    form_link_name='Program'
    
    url = models.CharField(max_length=80)
    name = models.CharField(max_length=80)
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    director_email = models.EmailField() # director contact email address used for from field and display
    director_cc_email = models.EmailField(blank=True, default='', help_text='If set, automated outgoing mail (except class cancellations) will be sent to this address instead of the director email. Use this if you do not want to spam the director email with teacher class registration emails. Otherwise, leave this field blank.') # "carbon-copy" address for most automated outgoing mail to or CC'd to directors (except class cancellations)
    director_confidential_email = models.EmailField(blank=True, default='', help_text='If set, confidential emails such as financial aid applications will be sent to this address instead of the director email.')
    program_size_max = models.IntegerField(null=True)
    program_allow_waitlist = models.BooleanField(default=False)
    program_modules = models.ManyToManyField(ProgramModule,
                         help_text='The set of enabled program functionalities. See ' +
                         '<a href="https://github.com/learning-unlimited/ESP-Website/blob/main/docs/admin/program_modules.rst">' +
                         'the documentation</a> for details.')
    class_categories = models.ManyToManyField('ClassCategories')

    #so we don't have to delete old ones and don't end up with
    # 3 seemingly-identical flags in the same program.
    flag_types = models.ManyToManyField('ClassFlagType',
                    blank=True,
                    help_text=format_lazy(
                    'The set of flags that can be used ' +
                    'to tag classes for this program. ' +
                    'Add flag types in <a href="%s">the admin panel</a>.',
                    urlresolvers.reverse_lazy('admin:program_classflagtype_changelist')))

    documents = generic.GenericRelation(Media, content_type_field='owner_type', object_id_field='owner_id')

    class Meta:
        app_label = 'program'
        db_table = 'program_program'

    USER_TYPES_WITH_LIST_FUNCS  = ['Student', 'Teacher', 'Volunteer']   # user types that have ProgramModule user filters
    USER_TYPE_LIST_FUNCS        = [user_type.lower()+'s' for user_type in USER_TYPES_WITH_LIST_FUNCS]   # the names of these filter methods, e.g. students(), teachers(), volunteers()
    USER_TYPE_LIST_NUM_FUNCS    = ['num_'+user_type for user_type in USER_TYPE_LIST_FUNCS]  # the names of the num methods, e.g. num_students(), num_teachers()
    USER_TYPE_LIST_DESC_FUNCS   = [user_type.lower()+'Desc' for user_type in USER_TYPES_WITH_LIST_FUNCS]    # the names of the description methods, e.g. studentDesc(), teacherDesc()

    @classmethod
    def setup_user_filters(cls):
        """
        Setup for the ProgramModule user filters
        """
        if not hasattr(cls, cls.USER_TYPE_LIST_FUNCS[0]):
            for i, user_type in enumerate(cls.USER_TYPE_LIST_FUNCS):
                setattr(cls, user_type, cls.get_users_from_module(user_type))
                setattr(cls, cls.USER_TYPE_LIST_NUM_FUNCS[i], cls.counts_from_query_dict(getattr(cls, user_type)))

    def get_absolute_url(self):
        return "/manage/"+self.url+"/main"
    
    @cache_function
    def isUsingStudentApps(self):
        from esp.program.models.app_ import StudentAppQuestion
        return bool(StudentAppQuestion.objects.filter(program=self) | StudentAppQuestion.objects.filter(subject__parent_program=self))
    isUsingStudentApps.depend_on_model('program.StudentAppQuestion')

    @cache_function
    def checkitems_all_cached(self):
        """  The main Manage page requests checkitems.all() O(n) times in
        the number of classes in the program.  Minimize the number of these
        calls that actually hit the db. """
        return self.checkitems.all()
    checkitems_all_cached.depend_on_row('program.ProgramCheckItem', lambda item: {'self': item.program})

    get_teach_url = _get_type_url("teach")
    get_learn_url = _get_type_url("learn")
    get_manage_url = _get_type_url("manage")
    get_onsite_url = _get_type_url("onsite")

    def save(self, *args, **kwargs):
        
        retVal = super(Program, self).save(*args, **kwargs)
        
        return retVal

    def __unicode__(self):
        return self.niceName()

    def niceName(self):
        return self.name

    def niceSubName(self):
        return self.name

    @property
    def program_type(self):
        return self.url.split('/')[0]

    @property
    def program_instance(self):
        return '/'.join(self.url.split('/')[1:])

    def getUrlBase(self):
        """ gets the base url of this class """
        return self.url

    def getDocuments(self):
        return self.documents.all()

    def get_msg_vars(self, user, key):
        modules = self.getModules(user)
        for module in modules:
            retVal = module.get_msg_vars(user, key)
            if retVal is not None and retVal.strip():
                return retVal

        return u''
    
    @staticmethod
    def get_users_from_module(method_name):
        def get_users(self, QObjects=False):
            modules = self.getModules(None)
            users = OrderedDict()
            for module in modules:
                tmpusers = getattr(module, method_name)(QObjects)
                if tmpusers is not None:
                    users.update(tmpusers)
            return users
        get_users.__name__  = method_name
        get_users.__doc__   = "Returns a dictionary of different sets of %s for this program, as defined by the enabled ProgramModules" % method_name
        return get_users

    @staticmethod
    def counts_from_query_dict(query_func):
        def _get_num(self):
            result = query_func(self, QObjects=False)
            result_dict = {}
            for key, value in result.iteritems():
                if isinstance(value, QuerySet):
                    result_dict[key] = value.count()
                else:
                    result_dict[key] = len(value)
            return result_dict
        _get_num.__name__   = "num_" + query_func.__name__
        _get_num.__doc__    = "Returns a dictionary of the sizes of the various sets of %s that are returned by Program.%s()" % (query_func.__name__, query_func.__name__)
        return _get_num

    @cache_function
    def capacity_by_section_id(self):
        capacities = {}
        for sec in self.sections():
            capacities[sec.id] = sec.capacity
        return capacities
    #   Clear this cache on any ClassSection capacity update... kind of brute force, but oh well.
    #   WARNING: Not sure if this usage is correct, can someone check?
    capacity_by_section_id.depend_on_cache('program.ClassSection._get_capacity', lambda **kwargs: {})

    def checked_in_by_section_id(self):
        from esp.program.models.class_ import sections_in_program_by_id
        section_ids = sections_in_program_by_id(self)
    
        counts = {}
        checked_in_ids = self.students()['attended'].values_list('id', flat=True)
    
        reg_type = RegistrationType.get_map()['Enrolled']

        regs = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self).filter(user__id__in=checked_in_ids, relationship=reg_type).values('user', 'section')
        for reg in regs:
            if reg['section'] not in counts:
                counts[reg['section']] = 0
            counts[reg['section']] += 1
                
        return counts
        
    def student_counts_by_section_id(self):
        from esp.program.models.class_ import sections_in_program_by_id
        section_ids = sections_in_program_by_id(self)
        
        class_cachekey = "class_size_counter_%d"
        counts = cache.get_many([class_cachekey % x for x in section_ids])

        clean_counts = {}
        missing_secs = set()

        for section_id in section_ids:
            clean_count = counts.get(class_cachekey % section_id, None)
            if not clean_count:
                missing_secs.add(section_id)
            clean_counts[section_id] = clean_count

        if len(missing_secs) != 0:
            initial_catalog_queryset = ClassSubject.objects.filter(sections__in=missing_secs)
            catalog = ClassSubject.objects.catalog(self, initial_queryset = initial_catalog_queryset)
            for subject in catalog:
                for section in subject.get_sections():
                    if int(section.id) in missing_secs:
                        clean_counts[section.id] = section.num_students()  ## Also repopulates the cache.  Magic!

        return clean_counts

    @cache_function
    def getListDescriptions(self):
        desc = {}
        modules = self.getModules()
        for module in modules:
            for func in Program.USER_TYPE_LIST_DESC_FUNCS:
                if hasattr(module, func):
                    tmpdict = getattr(module, func)()
                    if tmpdict is not None:
                        desc.update(tmpdict)
        return desc
    getListDescriptions.depend_on_m2m('program.Program', 'program_modules', lambda program, module: {'self': program})

    def getLists(self, QObjects=False):
        from esp.users.models import ESPUser
        
        lists = self.students(QObjects)
        lists.update(self.teachers(QObjects))
        lists.update(self.volunteers(QObjects))
        learnmodules = self.getModules(None)
        teachmodules = self.getModules(None)

        
        for k, v in lists.items():
            lists[k] = {'list': v,
                        'description':''}

        desc = self.getListDescriptions()
                
        for k, v in desc.items():
            if k in lists:
                lists[k]['description'] = v
                
        for usertype in ESPUser.getTypes():
            lists['all_'+usertype.lower()+'s'] = {'description':
                                   usertype+'s in all of ESP',
                                   'list' : ESPUser.getAllOfType(usertype)}
        # Filtering by students is a really bad idea
        students_Q = lists['all_students']['list']
        # We can restore this one later if someone really needs it. As it is, I wouldn't mind killing
        # lists['all_former_students'] as well.
        del lists['all_students']
        yog_12 = ESPUser.YOGFromGrade(12, ESPUser.program_schoolyear(self))
        # This technically has a bug because of copy-on-write, but the other code has it too, and
        # our copy-on-write system isn't good enough yet to make checking duplicates feasible
        lists['all_current_students'] = {'description': 'Current students in all of ESP',
                'list': students_Q & Q(registrationprofile__student_info__graduation_year__gte = yog_12, registrationprofile__most_recent_profile = True)}
        lists['all_former_students'] = {'description': 'Former students in all of ESP',
                'list': students_Q & Q(registrationprofile__student_info__graduation_year__lt = yog_12, registrationprofile__most_recent_profile = True)}

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
                return ESPUser.objects.filter(id = -1)
                    
        union = reduce(operator.or_, [x for x in self.students(True).values() ])
        if QObject:
            return union
        else:
            return ESPUser.objects.filter(union).distinct()

    def teachers_union(self, QObject = False):
        import operator
        if len(self.teachers().values()) == 0:
            if QObject:
                return Q(id = -1)
            else:
                return ESPUser.objects.filter(id = -1)
        union = reduce(operator.or_, [x for x in self.teachers(True).values() ])
        if QObject:
            return union
        else:
            return ESPUser.objects.filter(union).distinct()   
 
    def volunteers_union(self, QObject = False):
        import operator
        if len(self.volunteers().values()) == 0:
            if QObject:
                return Q(id = -1)
            else:
                return ESPUser.objects.filter(id = -1)
        union = reduce(operator.or_, [x for x in self.volunteers(True).values() ])
        if QObject:
            return union
        else:
            return ESPUser.objects.filter(union).distinct()

    @cache_function
    def isFull(self):
        """ Can this program accept any more students? """

        # Some programs don't have caps; this is represented with program_size_max in [ 0, None ]
        if self.program_size_max is None or self.program_size_max == 0:
            return False

        students_dict = self.students(QObjects = True)
        if students_dict.has_key('classreg'):
            students_count = ESPUser.objects.filter(students_dict['classreg']).distinct().count()
        else:
            students_count = ESPUser.objects.filter(record__event="reg_confirmed",record__program=self).distinct().count()

        isfull = ( students_count >= self.program_size_max )

        return isfull
    isFull.depend_on_cache('program.ClassSection.num_students', lambda self=wildcard, **kwargs: {'self': self.parent_class.parent_program})
    isFull.depend_on_row('program.Program', lambda prog: {'self': prog})
    isFull.depend_on_row('users.Record', lambda rec: {}, lambda rec: rec.event == "reg_confirmed") #i'm not sure why the selector is empty, that's how it was for the confirmation dependency when it was a userbit

    @cache_function
    def open_class_registration(self):
        return self.getModuleExtension('ClassRegModuleInfo').open_class_registration
    open_class_registration.depend_on_row('modules.ClassRegModuleInfo', lambda crmi: {'self': crmi.get_program()})
    open_class_registration = property(open_class_registration)

    @cache_function
    def open_class_category(self):
        """Return the name of the open class category, as determined by the program tag.

        This assumes you've already created the Category manually.

        Returns:
          A ClassCategories object if one was found, or None.
        """
        pk = Tag.getProgramTag('open_class_category', self, default=None)
        cc = None
        if pk is not None:
            try:
                pk = int(pk)
                cc = ClassCategories.objects.get(pk=pk)
            except (ValueError, TypeError, ClassCategories.DoesNotExist) as e:
                pass
        if cc is None:
            cc = ClassCategories.objects.get_or_create(category="Walk-in Activity", symbol='W', seq=0)[0]
        return cc
    open_class_category.depend_on_model('tagdict.Tag')
    open_class_category.depend_on_model('program.ClassCategories')
    open_class_category = property(open_class_category)

    @cache_function
    def getScheduleConstraints(self):
        return ScheduleConstraint.objects.filter(program=self).select_related()
    getScheduleConstraints.depend_on_model('program.ScheduleConstraint')
    getScheduleConstraints.depend_on_model('program.BooleanToken')

    def lock_schedule(self, lock_level=1):
        """ Locks all schedule assignments for the program, for convenience
            (e.g. between scheduling some sections manually and running
            automatic scheduling).
        """
        from esp.resources.models import ResourceAssignment
        ResourceAssignment.objects.filter(target__parent_class__parent_program=self, lock_level__lt=lock_level).update(lock_level=lock_level)

    def isConfirmed(self, espuser):
        return Record.objects.filter(event="reg_confirmed",user=espuser,
                                     program=self).exists()
    
    """ These functions have been rewritten.  To avoid confusion, I've changed "ClassRooms" to
    "Classrooms."  So, if you try to call the old functions (which have no point anymore), then 
    you'll get an error and you'll notice that you need to change the call and its associated
    code.               -Michael P
    
    """
    def getClassrooms(self, timeslot=None):
        #   Returns the resources themselves.  See the function below for grouped-by-room.
        from esp.resources.models import ResourceType
        
        if timeslot is not None:
            return self.getResources().filter(event=timeslot, res_type=ResourceType.get_or_create('Classroom')).select_related()
        else:
            return self.getResources().filter(res_type=ResourceType.get_or_create('Classroom')).order_by('event').select_related()
    
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
                result[c.name].prog_available_times = c.available_times_html(self)
            else:
                result[c.name].timeslots.append(c.event)
            
        for c in result:
            result[c].timegroup = Event.collapse(result[c].timeslots)
        
        return result

    @cache_function
    def groupedClassrooms(self):

        classrooms = self.getClassrooms()
        
        result = self.collapsed_dict(classrooms)
        key_list = result.keys()
        key_list.sort()
        #   Turn this into a list instead of a dictionary.
        ans = [result[key] for key in key_list]

        return ans
    groupedClassrooms.depend_on_row('resources.Resource', lambda res: {'self': res.event.parent_program()})
    groupedClassrooms.depend_on_row(Event, lambda event: {'self': event.parent_program()})
        
    def addClassroom(self, classroom_form):
        from esp.program.modules.forms.resources import ClassroomForm
        
        #   Parse classroom form to create classroom and associated resources, group them,
        #   and save them.
        assert False, 'todo'
        
    def classes(self):
        return ClassSubject.objects.filter(parent_program = self).order_by('id')        

    @cache_function
    def class_ids_implied(self):
        """ Returns the class ids implied by classes in this program. Returns [-1] for none so the cache doesn't keep getting hit. """
        retVal = set([])
        for c in self.classes():
            for imp in c.classimplication_set.all():
                retVal = retVal.union(imp.member_id_ints)
        if len(retVal) < 1:
            retVal = [-1]
        retVal = list(retVal)
        return retVal
    class_ids_implied.depend_on_row('program.ClassImplication', lambda ci: {'self': ci.cls.parent_program})

    def sections(self):
        return ClassSection.objects.filter(parent_class__parent_program=self).distinct().order_by('id').select_related('parent_class')

    def getTimeSlots(self, types=None, exclude_types=None):
        """ Get the time slots for a program. 
            A flag, exclude_types, allows you to restrict which types of timeslots
            are grabbed.  You can also provide a list of timeslot types to include.
            The default behavior is to include only class time slots.  See the
            install() function in esp/esp/cal/models.py for a list of time slot types.
        """
        qs = Event.objects.filter(program=self)
        if exclude_types is not None:
            qs = qs.exclude(event_type__description__in=exclude_types)
        elif types is not None:
            qs = qs.filter(event_type__description__in=types)
        else:
            qs = qs.filter(event_type__description='Class Time Block')
        return qs.select_related('event_type').order_by('start')

    def num_timeslots(self):
        return len(self.getTimeSlots())

    #   In situations where you just want a list of all time slots in the program,
    #   that can be cached.
    @cache_function
    def getTimeSlotList(self, include_all=False):
        if include_all:
            return list(self.getTimeSlots(exclude_types=[]))
        else:
            return list(self.getTimeSlots())
    getTimeSlotList.depend_on_model('cal.Event')

    def total_duration(self):
        """ Returns the total length of the events in this program, as a timedelta object. """
        ts_list = Event.collapse(list(self.getTimeSlots()), tol=timedelta(minutes=15))
        time_sum = timedelta()
        for t in ts_list:
            time_sum = time_sum + (t.end - t.start)
        return time_sum

    def dates(self):
        result = []
        for ts in self.getTimeSlotList():
            ts_day = date(ts.start.year, ts.start.month, ts.start.day)
            if ts_day not in result:
                result.append(ts_day)
        return result
    
    def date_range(self):
        """ Returns string range from earliest timeslot to latest timeslot, or NoneType if no timeslots set """
        dates = self.getTimeSlots()

        if dates:
            d1 = min(dates).start
            d2 = max(dates).end
            if d1.year == d2.year:
                if d1.month == d2.month:
                    if d1.day == d2.day:
                        return u'%s' % d1.strftime('%b. %d, %Y').decode('utf-8')
                    else:
                        return u'%s - %s' % (d1.strftime('%b. %d').decode('utf-8'), d2.strftime('%d, %Y').decode('utf-8'))
                else:
                    return u'%s - %s' % (d1.strftime('%b. %d').decode('utf-8'), d2.strftime('%b. %d, %Y').decode('utf-8'))
            else:
                return u'%s - %s' % (d1.strftime('%b. %d, %Y').decode('utf-8'), d2.strftime('%b. %d, %Y').decode('utf-8'))
        else:
            return None

    @cache_function
    def getResourceTypes(self, include_classroom=False, include_global=None):
        #   Show all resources pertaining to the program that aren't these two hidden ones.
        from esp.resources.models import ResourceType
        
        if include_classroom:
            exclude_types = []
        else:
            exclude_types = [ResourceType.get_or_create('Classroom')]
        
        if include_global is None:
            include_global = Tag.getTag('allow_global_restypes')

        if include_global:
            Q_filters = Q(program=self) | Q(program__isnull=True)
        else:
            Q_filters = Q(program=self)
        
        return ResourceType.objects.filter(Q_filters).exclude(id__in=[t.id for t in exclude_types]).order_by('priority_default')
    getResourceTypes.depend_on_model('resources.ResourceType')
    getResourceTypes.depend_on_model('tagdict.Tag')

    def getResources(self):
        from esp.resources.models import Resource
        return Resource.objects.filter(event__program=self)
    
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
        crmi = self.getModuleExtension(ClassRegModuleInfo)
        if crmi and crmi.class_max_duration is not None:
            max_seconds = crmi.class_max_duration * 60
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
        return Survey.objects.filter(program=self)
    
        
    def getLineItemTypes(self, user=None, required=True):
        from esp.accounting.controllers import ProgramAccountingController
        pac = ProgramAccountingController(self)
        if required:
            li_types = list(pac.get_lineitemtypes(required_only=True))
        else:
            li_types = list(pac.get_lineitemtypes(optional_only=True))

        return li_types

    @cache_function
    def getModules_cached(self, tl = None):
        """ Gets a list of modules for this program. """
        from esp.program.modules import base

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
        return modules
    getModules_cached.depend_on_row('program.Program', lambda prog: {'self': prog})
    getModules_cached.depend_on_model('program.ProgramModule')
    getModules_cached.depend_on_row('modules.ProgramModuleObj', lambda mod: {'self': mod.program})
    # I've only included the module extensions we still seem to use.
    # Feel free to adjust. -ageng 2010-10-23
    getModules_cached.depend_on_row('modules.ClassRegModuleInfo', lambda modinfo: {'self': modinfo.module.program})
    getModules_cached.depend_on_row('modules.StudentClassRegModuleInfo', lambda modinfo: {'self': modinfo.module.program})

    def getModules(self, user = None, tl = None):
        """ Gets modules for this program, optionally attaching a user. """
        modules = self.getModules_cached(tl)
        if user:
            for module in modules:
                module.setUser(user)
        #   Populate the view attributes so they can be cached
        for module in modules:
            module.get_all_views()
            module.get_main_view()
        return modules

    @cache_function
    def hasModule(self, name):
        """ Tests whether a program has the given module enabled, cachedly. name should be a module name, like 'AvailabilityModule'. """
        return self.program_modules.filter(handler=name).exists()
    hasModule.depend_on_row('program.Program', lambda prog: {'self': prog})
    hasModule.depend_on_model('program.ProgramModule')
    hasModule.depend_on_row('modules.ProgramModuleObj', lambda module: {'self': module.program})
    hasModule.depend_on_m2m('program.Program', 'program_modules', lambda program, module: {'self': program})

    @cache_function
    def getModule(self, name):
        """ Returns the specified module for this program if it is enabled.
            'name' should be a module name like 'AvailabilityModule'. """

        if self.hasModule(name):
            #   Sometimes there are multiple modules with the same handler.
            #   This function is not choosy, since the return value
            #   is typically used just to access a view function.
            return ProgramModuleObj.getFromProgModule(self, self.program_modules.filter(handler=name)[0])
        else:
            return None
    getModule.depend_on_cache(hasModule, lambda self=wildcard, name=wildcard, **kwargs: {'self': self, 'name': name})

    @cache_function
    def getModuleViews(self, main_only=False, tl=None):
        modules = self.getModules_cached(tl)
        result = {}
        for mod in modules:
            tl = mod.module.module_type
            if main_only:
                if mod.main_view:
                    result[(tl, mod.main_view)] = mod
            else:
                for view in mod.views:
                    result[(tl, view)] = mod
        return result
    getModuleViews.depend_on_cache(getModules_cached, lambda **kwargs: {})
    
    def getModuleExtension(self, ext_name_or_cls, module_id=None):
        """ Get the specified extension (e.g. ClassRegModuleInfo) for a program.
        This avoids actually looking up the program module first. """
        # We don't actually want to cache this in memcached:
        # If its value changes in the middle of a page load, we don't want to switch to the new value.
        # Also, the method is called quite often, so it adds cache load.
        # Program objects are assumed to not persist across page loads generally,
        # so the following should be marginally safer:
        
        if not hasattr(self, "_moduleExtension"):
            self._moduleExtension = {}

        key = (ext_name_or_cls, module_id)
        if key in self._moduleExtension:
            return self._moduleExtension[key]
        
        ext_cls = None
        if isinstance(ext_name_or_cls, basestring):
            mod = __import__('esp.program.modules.module_ext', (), (), ext_name_or_cls)
            ext_cls = getattr(mod, ext_name_or_cls)
        else:
            ext_cls = ext_name_or_cls

        if module_id:
            try:
                extension = ext_cls.objects.filter(module__id=module_id).select_related()[0]
            except:
                extension = ext_cls()
                extension.module_id = module_id
                extension.save()
        else:
            try:
                extension = ext_cls.objects.filter(module__program__id=self.id).select_related()[0]
            except:
                extension = None
                
        self._moduleExtension[key] = extension
                
        return extension

    @cache_function
    def getColor(self):
        if hasattr(self, "_getColor"):
            return self._getColor

        modinfo = self.getModuleExtension(ClassRegModuleInfo)
        retVal = None
        if modinfo:
            retVal = modinfo.color_code

        self._getColor = retVal
        return retVal
    getColor.depend_on_row('modules.ClassRegModuleInfo', lambda crmi: {'self': crmi.module.program})
    
    def visibleEnrollments(self):
        """
        Returns whether class enrollments should show up in the catalog.
        This originally returned true if class registration was fully open.
        Now it's just a checkbox in the StudentClassRegModuleInfo.
        """
        options = self.getModuleExtension('StudentClassRegModuleInfo')
        return options.visible_enrollments
        
    def getVolunteerRequests(self):
        return VolunteerRequest.objects.filter(timeslot__program=self).order_by('timeslot__start')
    
    @cache_function
    def getShirtInfo(self):
        shirt_count = defaultdict(lambda: defaultdict(int))
        teacher_dict = self.teachers()
        if teacher_dict.has_key('class_approved'):
            query = teacher_dict['class_approved']
            query = query.filter(registrationprofile__most_recent_profile=True)
            query = query.values_list('registrationprofile__teacher_info__shirt_type',
                                      'registrationprofile__teacher_info__shirt_size')
            query = query.annotate(people=Count('id', distinct=True))

            for row in query:
                shirt_type, shirt_size, count = row
                shirt_count[shirt_type][shirt_size] = count

        shirts = {}
        shirts['teachers'] = [ { 'type': shirt_type[1], 'distribution':[ shirt_count[shirt_type[0]][shirt_size[0]] for shirt_size in shirt_sizes ] } for shirt_type in shirt_types ]

        return {'shirts' : shirts, 'shirt_sizes' : shirt_sizes, 'shirt_types' : shirt_types }
    #   Update cache whenever a class is approved or a teacher changes their profile
    getShirtInfo.depend_on_row('program.ClassSubject', lambda cls: {'self': cls.parent_program})
    getShirtInfo.depend_on_model('users.TeacherInfo')

    @cache_function
    def incrementGrade(self): 
        """
        Get the value of the "increment_default_grade_levels" tag.

        This tag increments the effective school year of the program.
        Also affects how grade ranges for this program are displayed,
        to say "rising Xth grade" rather than just X.

        See ESPUser.program_schoolyear.
        """
        return int(Tag.getBooleanTag('increment_default_grade_levels', self, False))
    incrementGrade.depend_on_row('tagdict.Tag', lambda tag: {'self' :  tag.target})
    
    def priorityLimit(self):
        studentregmodule = self.getModuleExtension('StudentClassRegModuleInfo')
        if studentregmodule and studentregmodule.priority_limit > 0:
            return studentregmodule.priority_limit
        else: 
            return 1
    
    def useGradeRangeExceptions(self):
        studentregmodule = self.getModuleExtension('StudentClassRegModuleInfo')
        if studentregmodule:
            return studentregmodule.use_grade_range_exceptions
        else:
            return False
    
    def getDirectorCCEmail(self):
        if self.director_cc_email:
            return self.director_cc_email
        else:
            return self.director_email

    def getDirectorConfidentialEmail(self):
        if self.director_confidential_email:
            return self.director_confidential_email
        else:
            return self.getDirectorCCEmail()

    @cache_function
    def by_prog_inst(cls, program, instance):
        prog_inst = Program.objects.select_related().get(url='%s/%s' % (program, instance))
        return prog_inst
    by_prog_inst.depend_on_row('program.Program', lambda prog: {'program': prog})
    by_prog_inst = classmethod(by_prog_inst)

    def _sibling_discount_get(self):
        """
        Memoizes and returns the amount of the sibling_discount Tag, defaulting
        to 0.00.
        """
        if hasattr(self, "_sibling_discount"):
            return self._sibling_discount
        self._sibling_discount = Decimal(Tag.getProgramTag('sibling_discount', program=self, default='0.00'))
        return self._sibling_discount

    def _sibling_discount_set(self, value):
        if value is not None:
            self._sibling_discount = Decimal(value)
            Tag.setTag('sibling_discount', target=self, value=self._sibling_discount)
        else:
            self._sibling_discount = Decimal('0.00')
            Tag.objects.filter(key='sibling_discount', object_id=self.id).delete()

    sibling_discount = property(_sibling_discount_get, _sibling_discount_set)

    @property
    def splashinfo_objects(self):
        """
        Memoizes and returns the dictionary of students who have sibling
        discounts for this program.
        """
        if hasattr(self, "_splashinfo_objects"):
            return self._splashinfo_objects
        self._splashinfo_objects = dict(SplashInfo.objects.filter(program=self, siblingdiscount=True).distinct().values_list('student', 'siblingdiscount'))
        return self._splashinfo_objects

Program.setup_user_filters()


class SplashInfo(models.Model):
    """ A model that can be used to track additional student preferences specific to
        a program.  Stanford has used this for lunch selection and a sibling discount.
        The data is manipulated by a separate program module, SplashInfoModule,
        which produces an additional registration step if enabled.
    """
    student = AjaxForeignKey(ESPUser)
    #   Program field may be empty for backwards compatibility with Stanford data
    program = AjaxForeignKey(Program, null=True)
    lunchsat = models.CharField(max_length=32, blank=True, null=True)
    lunchsun = models.CharField(max_length=32, blank=True, null=True)
    siblingdiscount = models.NullBooleanField(default=False, blank=True)
    siblingname = models.CharField(max_length=64, blank=True, null=True)
    submitted = models.NullBooleanField(default=False, blank=True)

    class Meta:
        app_label = 'program'
        db_table = 'program_splashinfo'

    def __unicode__(self):
        return u'Lunch/sibling info for %s at %s' % (self.student, self.program)

    @staticmethod
    def hasForUser(user, program=None):
        if program:
            q = SplashInfo.objects.filter(student=user, program=program)
        else:
            q = SplashInfo.objects.filter(student=user)
        return (q.count() > 0) and q[0].submitted

    @staticmethod
    def getForUser(user, program=None):
        if program:
            q = SplashInfo.objects.filter(student=user, program=program)
        else:
            q = SplashInfo.objects.filter(student=user)
        if q.count() > 0:
            return q[0]
        else:
            n = SplashInfo(student=user, program=program)
            n.save()
            return n    
            
    def pretty_version(self, attr_name):
        #   Look up choices
        tag_data = Tag.getTag('splashinfo_choices', target=self.program)
        if not tag_data: tag_data = Tag.getTag('splashinfo_choices')
        
        #   Check for matching item in list of choices
        if tag_data:
            tag_struct = json.loads(tag_data)
            for item in tag_struct[attr_name]:
                if item[0] == getattr(self, attr_name):
                    return item[1].decode('utf-8')
                    
        return u'N/A'
    
    def pretty_satlunch(self):
        return self.pretty_version('lunchsat')

    def pretty_sunlunch(self):
        return self.pretty_version('lunchsun')

    def execute_sibling_discount(self):
        if self.siblingdiscount:
            from esp.accounting.controllers import IndividualAccountingController
            from esp.accounting.models import Transfer
            iac = IndividualAccountingController(self.program, self.student)
            source_account = iac.default_finaid_account()
            dest_account = iac.default_source_account()
            line_item_type = iac.default_siblingdiscount_lineitemtype()
            transfer, created = Transfer.objects.get_or_create(source=source_account, destination=dest_account, user=self.student, line_item=line_item_type, amount_dec=Decimal('20.00'))
            return transfer

    def save(self):
        from esp.accounting.controllers import IndividualAccountingController

        #   We have two things to put in: "Saturday Lunch" and "Sunday Lunch".  
        #   If they are not there, they will be created.  These names are hard coded.
        from esp.accounting.models import LineItemType
        LineItemType.objects.get_or_create(program=self.program, text='Saturday Lunch')
        LineItemType.objects.get_or_create(program=self.program, text='Sunday Lunch')

        #   Figure out how much everything costs
        cost_info = json.loads(Tag.getProgramTag('splashinfo_costs', self.program, default='{}'))

        #   Save accounting information
        iac = IndividualAccountingController(self.program, self.student)

        if not self.lunchsat or self.lunchsat == 'no':
            iac.set_preference('Saturday Lunch', 0)
        elif 'lunchsat' in cost_info:
            iac.set_preference('Saturday Lunch', 1, cost_info['lunchsat'][self.lunchsat])

        if not self.lunchsun or self.lunchsun == 'no':
            iac.set_preference('Sunday Lunch', 0)
        elif 'lunchsun' in cost_info:
            iac.set_preference('Sunday Lunch', 1, cost_info['lunchsun'][self.lunchsun])
        
        super(SplashInfo, self).save()


class RegistrationProfile(models.Model):
    """ A student registration form """
    user = AjaxForeignKey(ESPUser)
    program = models.ForeignKey(Program, blank=True, null=True)
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
    most_recent_profile = models.BooleanField(default=False)

    old_text_reminder = models.NullBooleanField(db_column='text_reminder')  ## Kept around for database-migration purposes

    ## Oops, I didn't see this field, and I reimplemented its functionality...
    ## Wrap it for backwards compatibility. -- aseering 8/18/2010
    def _get_text_reminder(self):
        if not self.contact_user:
            return None
        return self.contact_user.receive_txt_message
    def _set_text_reminder(self, val):
        if not self.contact_user:
            contact_user = ContactInfo()
            contact_user.first_name = self.user.first_name
            contact_user.last_name = self.user.last_name
            contact_user.save()
            self.contact_user = contact_user
            self.save()
        self.contact_user.receive_txt_message = val
        self.contact_user.save()
    text_reminder = property(_get_text_reminder, _set_text_reminder)

    class Meta:
        app_label = 'program'
        db_table = 'program_registrationprofile'

    @cache_function
    def getLastProfile(user):
        regProf = None
        
        if isinstance(user.id, (int, long)):
            try:
                regProf = RegistrationProfile.objects.filter(user__exact=user).select_related().latest('last_ts')
            except:
                pass

        if regProf != None:
            return regProf
        
        regProf = RegistrationProfile()
        regProf.user = ESPUser(user)

        return regProf
    getLastProfile.depend_on_row('program.RegistrationProfile', lambda profile: {'user': profile.user})
    getLastProfile = staticmethod(getLastProfile) # a bit annoying, but meh

    def confirmStudentReg(self, user):
        """ Confirm the specified user's registration in the program """
        records = Record.objects.filter(user=self.user, event="reg_confirmed")
        if records.count() == 0:
            record = Record.objects.create(user=self.user, event="reg_confirmed", program=self.program)

    def save(self, *args, **kwargs):
        """ update the timestamp and clear getLastProfile cache """
        self.last_ts = datetime.now()
        RegistrationProfile.objects.filter(user = self.user, most_recent_profile = True).update(most_recent_profile = False)
        self.most_recent_profile = True
        super(RegistrationProfile, self).save(*args, **kwargs)
        
    @cache_function
    def getLastForProgram(user, program):
        """ Returns the newest RegistrationProfile attached to this user and this program (or any ancestor of this program). """
        if user.is_anonymous():
            regProfList = RegistrationProfile.objects.none()
        else:
            regProfList = (RegistrationProfile.objects
                           .filter(user__exact=user, program__exact=program)
                           .select_related(
                               'user', 'program', 'contact_user',
                               'contact_guardian', 'contact_emergency',
                               'student_info', 'teacher_info', 'guardian_info',
                               'educator_info')
                           .order_by('-last_ts','-id')[:1])
        if len(regProfList) < 1:
            regProf = RegistrationProfile.getLastProfile(user)
            regProf.program = program
            if regProf.id is not None:
                regProf.id = None
                if (datetime.now() - regProf.last_ts).days <= 5:
                    regProf.save()
        else:
            regProf = regProfList[0]
        return regProf
    # Thanks to our attempts to be smart and steal profiles from other programs,
    # the cache can't depend only on profiles with the same (user, program).
    getLastForProgram.depend_on_row('program.RegistrationProfile', lambda rp: {'user': rp.user})
    getLastForProgram = staticmethod(getLastForProgram)
            
    def __unicode__(self):
        if self.program_id == None:
            return u'<Registration for %s>' % unicode(self.user)
        if self.user is not None:
            return u'<Registration for %s in %s>' % (unicode(self.user), unicode(self.program))


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
    def preregistered_classes(self,verbs=None):
        return ESPUser(self.user).getSectionsFromProgram(self.program,verbs=verbs)
    
    def registered_classes(self):
        return ESPUser(self.user).getEnrolledSections(program=self.program)


class TeacherBio(models.Model):
    """ This is the biography of a teacher."""

    program = models.ForeignKey(Program, blank=True, null=True)
    user    = AjaxForeignKey(ESPUser)
    bio     = models.TextField(blank=True, null=True)
    slugbio = models.CharField(max_length=50, blank=True, null=True)
    picture = models.ImageField(height_field = 'picture_height', width_field = 'picture_width', upload_to = "uploaded/bio_pictures/%y_%m/",blank=True, null=True)
    picture_height = models.IntegerField(blank=True, null=True)
    picture_width  = models.IntegerField(blank=True, null=True)
    last_ts = models.DateTimeField(auto_now = True)    
    hidden = models.BooleanField(default=False)

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
    user    = AjaxForeignKey(ESPUser, editable = False)

    reduced_lunch = models.BooleanField(verbose_name = 'Do you receive free/reduced lunch at school?', blank=True, default=False)

    household_income = models.CharField(verbose_name = 'Approximately what is your household income (round to the nearest $10,000)?', null=True, blank=True,
                        max_length=12)

    extra_explaination = models.TextField(verbose_name = 'Please describe in detail your financial situation this year', null=True, blank=True)

    student_prepare = models.BooleanField(verbose_name = 'Did anyone besides the student fill out any portions of this form?', blank=True, default=False)

    done = models.BooleanField(default=False, editable=False)

    @property
    def approved(self):
        return (self.financialaidgrant_set.all().count() > 0)

    class Meta:
        app_label = 'program'
        db_table = 'program_financialaidrequest'
        unique_together = ('program', 'user')

    def __unicode__(self):
        """ Represent this as a string. """
        if self.reduced_lunch:
            reducedlunch = u"(Free Lunch)"
        else:
            reducedlunch = u''
            
        explanation = self.extra_explaination
        if explanation is None:
            explanation = u''
        elif len(explanation) > 40:
            explanation = explanation[:40] + u"..."


        string = u"%s (%s@%s) for %s (%s, %s) %s"%\
                 (ESPUser(self.user).name(), self.user.username, settings.DEFAULT_HOST, self.program.niceName(), self.household_income, explanation, reducedlunch)

        if self.done:
            string = u"Finished: [" + string + u"]"

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

    class Meta:
        app_label = 'program'

    def get_expr(self):
        return self.exp.subclass_instance()
    #   Renamed to expr to avoid conflicting with Django SQL evaluator "expression"
    expr = property(get_expr)

    def __unicode__(self):
        return u'[%d] %s' % (self.seq, self.text)

    @cache_function
    def subclass_instance(self):
        return get_subclass_instance(BooleanToken, self)
    subclass_instance.depend_on_row('program.BooleanToken', lambda bt: {'self': bt})

    @staticmethod
    def evaluate(stack, *args, **kwargs):
        """ Evaluate a stack of Boolean tokens. 
            Operations (including the basic ones defined below) take their
            arguments off the stack.
        """
        value = None
        stack = list(stack)
        while (value is None) and (len(stack) > 0):
            token = stack.pop()     #   Used to be .subclass_instance() - this is now in BooleanExpression.get_stack()
            
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

    class Meta:
        app_label = 'program'

    label = models.CharField(max_length=80, help_text='Description of the expression')

    def __unicode__(self):
        return u'(%d tokens) %s' % (len(self.get_stack()), self.label)

    def subclass_instance(self):
        return get_subclass_instance(BooleanExpression, self)

    @cache_function
    def get_stack(self):
        return [s.subclass_instance() for s in self.booleantoken_set.all().order_by('seq')]
    get_stack.depend_on_row('program.BooleanToken', lambda token: {'self': token.exp})
        
    def reset(self):
        self.booleantoken_set.all().delete()

    def add_token(self, token_or_value, seq=None, duplicate=True):
        my_stack = self.get_stack()
        if isinstance(token_or_value, basestring):
            new_token = BooleanToken(text=token_or_value)
        elif duplicate:
            token_type = type(token_or_value)
            #   print 'Adding duplicate of token %s, type %s, to %s' % (token_or_value.id, token_type.__name__, unicode(self))
            new_token = token_type()
            #   Copy over fields that don't describe relations
            for item in new_token._meta.fields:
                if not item.__class__.__name__ in ['AutoField', 'OneToOneField']:
                    setattr(new_token, item.name, getattr(token_or_value, item.name))
        else:
            new_token = token_or_value
        if seq is None:
            if len(my_stack) > 0:
                new_token.seq = self.get_stack()[-1].seq + 10
            else:
                new_token.seq = 0
        else:
            new_token.seq = seq
        new_token.exp = self
        new_token.save()
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
    def __init__(self, user, program):
        if not isinstance(user, ESPUser):
            user = ESPUser(user)
        self.program = program
        self.user = user
        self.populate()

    def populate(self):
        result = {}
        for t in self.program.getTimeSlotList():
            result[t.id] = []
        sl = self.user.getEnrolledSectionsFromProgram(self.program)
        for s in sl:
            for m in s._timeslot_ids:
                result[m].append(s)
        self.map = result
        return self.map

    def add_section(self, sec):
        for t in sec.timeslot_ids():
            self.map[t].append(sec)
            
    def remove_section(self, sec):
        for t in sec.timeslot_ids():
            if sec in self.map[t]:
                self.map[t].remove(sec)

    def __marinade__(self):
        import hashlib
        import pickle
        return 'ScheduleMap_%s' % hashlib.md5(pickle.dumps(self)).hexdigest()[:8]
        
    def __unicode__(self):
        return u'%s' % self.map

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

    class Meta:
        app_label = 'program'
    
    def __unicode__(self):
        return u'%s: "%s" requires "%s"' % (self.program.niceName(), unicode(self.condition), unicode(self.requirement))
    
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
                    if isinstance(fail_result, ScheduleMap):
                        self.schedule_map = fail_result
                    #   raise AjaxError('ScheduleConstraint says %s' % data)
                    return self.evaluate(self.schedule_map, recursive=False)
                else:
                    return False
        else:
            return True

    def handle_failure(self):
        #   Try the on_failure callback but be very lenient about it (fail silently)
        try:
            func_str = """def _f(schedule_map):
%s""" % ('\n'.join('    %s' % l.rstrip() for l in self.on_failure.strip().split('\n')))
            exec func_str
            result = _f(self.schedule_map)
            return result
        except Exception, inst:
            #   raise ESPError('Schedule constraint handler error: %s' % inst, log=False)
            pass
        #   If we got nothing from the on_failure function, just provide Nones.
        return (None, None)

class ScheduleTestTimeblock(BooleanToken):
    """ A boolean value that keeps track of a timeblock. 
        This is an abstract base class that doesn't define
        the boolean_value function.
    """
    timeblock = models.ForeignKey(Event, help_text='The timeblock that this schedule test pertains to')

    class Meta:
        app_label = 'program'

class ScheduleTestOccupied(ScheduleTestTimeblock):
    """ Boolean value testing: Does the schedule contain at least one
        section at the specified time?
    """
    class Meta:
        app_label = 'program'

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

    class Meta:
        app_label = 'program'
            
class ScheduleTestSectionList(ScheduleTestTimeblock):
    """ Boolean value testing: Does the schedule contain one of the specified
        sections at the specified time?
    """
    section_ids = models.TextField(help_text='A comma separated list of ClassSection IDs that can be selected for this timeblock')

    class Meta:
        app_label = 'program'
    
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
    

class VolunteerRequest(models.Model):
    program = models.ForeignKey(Program)
    timeslot = models.ForeignKey('cal.Event')
    num_volunteers = models.PositiveIntegerField()

    class Meta:
        app_label = 'program'
    
    def num_offers(self):
        return self.volunteeroffer_set.count()
        
    def get_offers(self):
        return self.volunteeroffer_set.all()

    def __unicode__(self):
        return u'%s (%s)' % (self.timeslot.description, self.timeslot.short_time())

class VolunteerOffer(models.Model):
    request = models.ForeignKey(VolunteerRequest)
    confirmed = models.BooleanField()

    #   Fill out this if you're logged in...
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    
    #   ...or this if you haven't.
    email = models.EmailField(blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)
    
    shirt_size = models.CharField(max_length=5, blank=True, choices=shirt_sizes, null=True)
    shirt_type = models.CharField(max_length=20, blank=True, choices=shirt_types, null=True)
    
    comments = models.TextField(blank=True, null=True)

    class Meta:
        app_label = 'program'
    
    def __unicode__(self):
        return u'%s (%s, %s) for %s' % (self.name, self.email, self.phone, self.request)
    

""" This class provides the information that was provided by the DataTree
    anchor of each Userbit.  For example:
        URI V/Flags/Registration/Enrolled (name = 'Enrolled') -> 'name'
        Friendly name 'Student is enrolled in the class' -> 'description'
    In general, intermediate models for many-to-many relationships can 
    include a foreign key to this model unless it the relationships are
    inherently unambiguous.  There are too many different ways
    for students to be associated with a class for there to be a
    separate relationship for each (i.e. 'enrolled_students' field,
    'applied_students', etc.)
    
    Note: These models fit better in class_.py but cause validation errors
    due to Django's import scheme if they are placed there.
"""
class RegistrationType(models.Model):
    #   The 'key' (not really the primary key since we may want duplicate names)
    name = models.CharField(max_length=32)
    
    #   A more understandable name that is displayed by default, but has no effect on behavior
    displayName = models.CharField(max_length=32, blank=True, null=True)
    
    #   A more detailed description
    description = models.TextField(blank=True, null=True)
    
    #   Purely for bookkeeping on the part of administrators 
    #   without reading the whole description
    category = models.CharField(max_length=32)
    
    class Meta:
        unique_together = (("name", "category"),)
        app_label = 'program'
    
    @cache_function
    def get_cached(name, category):
        rt, created = RegistrationType.objects.get_or_create(name=name, defaults = {'category': category})
        return rt
    get_cached.depend_on_model('program.RegistrationType')
    get_cached = staticmethod(get_cached)

    @cache_function
    def get_map(include=None, category=None):
        #   If 'include' is specified, make sure we have keys named in that list
        if include:
            if not isinstance(category, str):
                raise ESPError('Need to supply category to RegistrationType.get_map() when passing include arguments', log=True)
            for name in include:
                type, created = RegistrationType.objects.get_or_create(name=name, category=category)
        
        #   Build a dictionary where names point to RegistrationType objects
        result = {}
        for item in RegistrationType.objects.all():
            result[item.name] = item
        return result
    get_map.depend_on_model('program.RegistrationType')
    get_map = staticmethod(get_map)

    def __unicode__(self):
        if self.displayName is not None and self.displayName != u"":
            return self.displayName
        else:
            return self.name

class StudentRegistration(ExpirableModel):
    """
    Model relating a student with a class section (interest, priority,
    enrollment, etc.).
    """
    section = AjaxForeignKey('ClassSection')
    user = AjaxForeignKey(ESPUser)
    relationship = models.ForeignKey(RegistrationType)

    class Meta:
        app_label = 'program'
    
    def __unicode__(self):
        return u'%s %s in %s' % (self.user, self.relationship, self.section)

class StudentSubjectInterest(ExpirableModel):
    """
    Model indicating a student interest in a class section.
    """
    subject = AjaxForeignKey('ClassSubject')
    user = AjaxForeignKey(ESPUser)

    class Meta:
        app_label = 'program'

    def __unicode__(self):
        return u'%s interest in %s' % (self.user, self.subject)
    
from esp.program.models.class_ import *
from esp.program.models.app_ import *
from esp.program.models.flags import *

def install():
    from esp.program.models.class_ import install as install_class
    print "Installing esp.program initial data..."
    install_class()

# The following are only so that we can refer to them in caching
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.resources.models import ResourceType
