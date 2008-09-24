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
from esp.users.models import UserBit, ContactInfo, StudentInfo, TeacherInfo, EducatorInfo, GuardianInfo, ESPUser
from esp.lib.markdown import markdown
from esp.qsd.models import QuasiStaticData
from datetime import datetime, timedelta
from django.core.cache import cache
from esp.miniblog.models import Entry
from django.db.models import Q
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError
from django.contrib import admin

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

    # aseering 3-19-2007 -- ??; no idea what this is for
    check_call = models.CharField(max_length=32, blank=True, null=True)

    # One of teach/learn/etc.; What is this module typically used for?
    module_type = models.CharField(max_length=32)

    # self.__name__, stored neatly in the database
    handler    = models.CharField(max_length=32)

    # Sequence orderer.  When ProgramModules are listed on a page, order them
    # from smallest to largest 'seq' value
    seq = models.IntegerField()

    # Secondary view functions associated with this ProgramModule
    aux_calls = models.CharField(max_length=512, blank=True, null=True)

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

        def __str__(self):
            return self.msg
    
    def __str__(self):
        return 'Program Module: %s' % self.admin_title

admin.site.register(ProgramModule)
    
    
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

    __str__ = __unicode__

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
        from esp.db.models import Q
        Q_ClassTeacher = Q(teacher__icontains = (user.first_name + ' ' + user.last_name)) |\
               Q(teacher_ids__icontains = ('|%s|' % user.id))
        Q_ClassStudent = Q(student_ids__icontains = ('|%s|' % user.id))
        #   We want to only show archive classes for teachers.  At least for now.
        Q_Class = Q_ClassTeacher #  | Q_ClassStudent
        return ArchiveClass.objects.filter(Q_Class).order_by('-year','-date','title')

class ArchiveClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'year', 'date', 'category', 'program', 'teacher')
    search_fields = ['description', 'title', 'program', 'teacher', 'category']
    pass
admin.site.register(ArchiveClass, ArchiveClassAdmin)
    

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

    anchor = AjaxForeignKey(DataTree) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    director_email = models.CharField(max_length=64)
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    program_size_max = models.IntegerField(null=True)
    program_modules = models.ManyToManyField(ProgramModule)

    class Meta:
        app_label = 'program'
        db_table = 'program_program'

    def checkitems_all_cached(self):
        """  The main Manage page requests checkitems.all() O(n) times in
        the number of classes in the program.  Minimize the number of these
        calls that actually hit the db. """
        CACHE_KEY = "PROGRAM__CHECKITEM__CACHE__%d" % self.id
        val = cache.get(CACHE_KEY)
        if val == None:
            val = self.checkitems.all()
            len(val)
            cache.set(CACHE_KEY, val, 1)
        
        return val

    get_teach_url = _get_type_url("teach")
    get_learn_url = _get_type_url("learn")
    get_manage_url = _get_type_url("manage")
    get_onsite_url = _get_type_url("onsite")

    def save(self):
        
        retVal = super(Program, self).save()
        
        return retVal

    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[-2:])
    
    def __str__(self):
        return str(self.anchor.parent.friendly_name) + ' ' + str(self.anchor.friendly_name)

    def parent(self):
        return self.anchor.parent

    def niceName(self):
        return str(self).replace("_", " ")

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
            print tmpdict
            if tmpdict is not None:
                desc.update(tmpdict)

        for k, v in desc.items():
            lists[k]['description'] = v
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

    def isFull(self, use_cache=True):
        """ Can this program accept any more students? """
        CACHE_KEY = "PROGRAM__ISFULL_%s" % self.id
        CACHE_DURATION = 10

        if use_cache:
            from django.core.cache import cache
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

        userbits = userbits.filter(Q(enddate__isnull=True) | Q(enddate__gte=datetime.now()))

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
        from esp.resources.models import ResourceType
        #   Filters down classrooms to those that are not taken.
        return filter(lambda x: x.is_available(), self.getClassrooms(timeslot))
    
    def collapsed_dict(self, resources):
        result = {}
        for c in resources:
            if c.name not in result:
                #   Make a dictionary with some helper variables for each resource.
                result[c.name] = c
                result[c.name].timeslots = [c.event]
            else:
                result[c.name].timeslots.append(c.event)
            result[c.name].furnishings = c.associated_resources()
            result[c.name].sequence = c.schedule_sequence(self)
            result[c.name].prog_available_times = c.available_times(self.anchor)
            
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
        from esp.resources.models import ResourceType
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

    def class_sections(self):
        return ClassSection.objects.filter(classsubject__parent_program = self).order_by('id')
    
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

    def sections(self):
        all_classes = self.classes()
        section_ids = []
        for c in all_classes:
            section_ids += [item['id'] for item in c.sections.all().values('id')]
        return ClassSection.objects.filter(id__in=section_ids).order_by('id')        

    def getTimeSlots(self):
        return Event.objects.filter(anchor=self.anchor).order_by('start')

    def total_duration(self):
        """ Returns the total length of the events in this program, as a timedelta object. """
        ts_list = self.getTimeSlots()
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
        exclude_types = [ResourceType.get_or_create('Classroom'), ResourceType.get_or_create('Teacher Availability')]
        
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
        exclude_types = [ResourceType.get_or_create('Classroom'), ResourceType.get_or_create('Teacher Availability')]
        
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
                        durationDict[durationSeconds / 3600.0] = \
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
        
    def getLineItemTypes(self, user=None):
        from esp.accounting_core.models import LineItemType, Balance
        
        li_types = list(LineItemType.objects.filter(anchor=GetNode(self.anchor.get_uri()+'/LineItemTypes/Required')))
        
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
    
    def getModuleExtension(self, ext_name_or_cls, module_id=None):
        """ Get the specified extension (e.g. ClassRegModuleInfo) for a program.
        This avoids actually looking up the program module first. """
        
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
                
        return extension

    def getColor(self):
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
        return retVal
    
    def visibleEnrollments(self):
        """
        Returns whether class enrollments should show up in the catalog.
        Current policy is that after everybody can sign up for one class, this returns True.
        """
        
        cache_key = 'PROGRAM_VISIBLEENROLLMENTS_%s' % self.id
        retVal = cache.get(cache_key)
        
        if retVal is None:
            reg_verb = GetNode('V/Deadline/Registration/Student/Classes/OneClass')
            retVal = False
            if UserBit.objects.filter(user__isnull=True, qsc=self.anchor, verb=reg_verb, startdate__lte=datetime.now()).count() > 0:
                retVal = True
            else:
                if UserBit.objects.filter(user__isnull=True, qsc__rangestart__lte=self.anchor.rangestart, qsc__rangeend__gte=self.anchor.rangeend, verb__rangestart__lte=reg_verb.rangestart, verb__rangeend__gte=reg_verb.rangeend, recursive=True, startdate__lte=datetime.now()).count() > 0:
                    retVal = True
            cache.set(cache_key, retVal, 9999)
        return retVal
    
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
        return Program.objects.select_related().get(anchor__name=instance, anchor__parent__name=program)

admin.site.register(Program)
    
    
class BusSchedule(models.Model):
    """ A scheduled bus journey associated with a program """
    program = models.ForeignKey(Program)
    src_dst = models.CharField(max_length=128)
    departs = models.DateTimeField()
    arrives = models.DateTimeField()

    class Meta:
        app_label = 'program'
        db_table = 'program_busschedule'

admin.site.register(BusSchedule)

    
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

    def __str__(self):
        return 'Profile for ' + str(self.teacher) + ' in ' + str(self.program)

admin.site.register(TeacherParticipationProfile)
    

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

admin.site.register(SATPrepRegInfo)


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
    email_verified  = models.BooleanField(default=False, blank=True, null = True)

    class Meta:
        app_label = 'program'
        db_table = 'program_registrationprofile'

    @staticmethod
    def getLastProfile(user):
        regProfList = RegistrationProfile.objects.filter(user__exact=user).order_by('-last_ts','-id')
        if len(regProfList) < 1:
            regProf = RegistrationProfile()
            regProf.user = user
        else:
            regProf = regProfList[0]
        return regProf

    def confirmStudentReg(self, user):
        """ Confirm the specified user's registration in the program """
        bits = UserBit.objects.filter(user=user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(self.anchor.tree_encode()) + "/Confirmation")).filter(Q(enddate__isnull=True)|Q(enddate__gte=datetime.now()))
        if bits.count() == 0:
            bit = UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))

    def cancelStudentRegConfirmation(self, user):
        """ Cancel the registration confirmation for the specified student """
        raise ESPError(), "Error: You can't cancel a registration confirmation!  Confirmations are final!"
        #for bit in UserBit.objects.filter(user=user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(self.anchor.tree_encode()) + "/Confirmation")).filter(Q(enddate__isnull=True)|Q(enddate__gte=datetime.now())):
        #    bit.expire()
        
    def save(self):
        """ update the timestamp """
        self.last_ts = datetime.now()
        super(RegistrationProfile, self).save()
        
    @staticmethod
    def getLastForProgram(user, program):
        """ Returns the newest RegistrationProfile attached to this user and this program (or any ancestor of this program). """
        regProfList = RegistrationProfile.objects.filter(user__exact=user,program__exact=program).order_by('-last_ts','-id')
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
    
    #   Note: these functions return ClassSections, not ClassSubjects.
    def preregistered_classes(self):
        return ESPUser(self.user).getSections(program=self.program)
    
    def registered_classes(self):
        return ESPUser(self.user).getEnrolledSections(program=self.program)

admin.site.register(RegistrationProfile)
    

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

    def save(self):
        """ update the timestamp """
        self.last_ts = datetime.now()
        if self.program_id is None:
            try:
                self.program = Program.objects.get(anchor = GetNode("Q/Programs/Dummy_Programs/Profile_Storage"))
            except:
                raise ESPError(), 'Error: There needs to exist an administrive program anchored at Q/Programs/Dummy_Programs/Profile_Storage.'

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

class TeacherBioAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'slugbio')
    search_fields = ['slugbio', 'bio']

admin.site.register(TeacherBio, TeacherBioAdmin)
    

class FinancialAidRequest(models.Model):
    """
    Student financial Aid Request
    """

    program = models.ForeignKey(Program, editable = False)
    user    = AjaxForeignKey(User, editable = False)

    approved = models.DateTimeField(blank=True, null=True)

    reduced_lunch = models.BooleanField(verbose_name = 'Do you receive free/reduced lunch at school?', null=True, blank=True)

    household_income = models.CharField(verbose_name = 'Approximately what is your household income (round to the nearest $10,000)?', null=True, blank=True,
                        max_length=12)

    extra_explaination = models.TextField(verbose_name = 'Please describe in detail your financial situation this year', null=True, blank=True)

    student_prepare = models.BooleanField(verbose_name = 'Did anyone besides the student fill out any portions of this form?', blank=True,null=True)

    done = models.BooleanField(default=False, editable=False)

    reviewed = models.BooleanField(default=False, verbose_name='Reviewed by Directors')

    amount_received = models.IntegerField(blank=True,null=True, verbose_name='Amount granted')
    amount_needed = models.IntegerField(blank=True,null=True, verbose_name='Amount due from student')

    class Meta:
        app_label = 'program'
        db_table = 'program_financialaidrequest'

    def save(self):
        """ If possible, find the student's invoice and update it to reflect the 
        financial aid that has been granted. """
        
        #   By default, the amount received is 0.  If this is the case, don't do
        #   any extra work.
        models.Model.save(self)
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
        charges = txn.lineitem_set.filter(anchor__rangestart__gte=anchor.rangestart, anchor__rangeend__lte=anchor.rangeend, anchor__parent__name='LineItemTypes')
       
        chg_amt = 0
        for li in charges:
            chg_amt += li.amount
        if self.amount_received > (-chg_amt):
            self.amount_received = -chg_amt
        
        #   Reverse all financial aid awards and add a new line item for this one.
        finaids = txn.lineitem_set.filter(anchor__rangestart__gte=anchor.rangestart, anchor__rangeend__lte=anchor.rangeend, anchor__parent__name='Accounts')
        rev_li_type, unused = LineItemType.objects.get_or_create(text='Financial Aid Reversal',anchor=funding_node['FinancialAid'])
        fwd_li_type, unused = LineItemType.objects.get_or_create(text='Financial Aid',anchor=funding_node['FinancialAid'])
        for li in finaids:
            if li.amount != 0:
                txn.add_item(self.user, rev_li_type, amount=-(li.amount))
        txn.add_item(self.user, fwd_li_type, amount=Decimal(str(self.amount_received)))
        
        

    def __str__(self):
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

admin.site.register(FinancialAidRequest)

from esp.program.models.class_ import *
from esp.program.models.app_ import *
