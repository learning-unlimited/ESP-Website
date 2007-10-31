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
from datetime import datetime
from django.core.cache import cache
from esp.miniblog.models import Entry
from django.db.models import Q
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError
    
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
            userlist += User.objects.filter(id = uid)
        return userlist
    
    def teachers(self):
        from esp.users.models import ESPUser
        userlist = []
        for uid in self.teacher_ids.strip('|').split('|'):
            userlist += User.objects.filter(id = uid)
        return userlist
    
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
    

    
    
class Program(models.Model):
    """ An ESP Program, such as HSSP Summer 2006, Splash Fall 2006, Delve 2005, etc. """

    anchor = AjaxForeignKey(DataTree) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    director_email = models.CharField(maxlength=64)
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    program_size_max = models.IntegerField(null=True)
    program_modules = models.ManyToManyField(ProgramModule)

    def _get_type_url(self, type):
        if hasattr(self, '_type_url'):
            if type in self._type_url:
                return self._type_url[type]
        else:
            self._type_url = {}

        self._type_url[type] = '/%s/%s/' % (type, '/'.join(self.anchor.tree_encode()[2:]))

        return self._type_url[type]

    def __init__(self, *args, **kwargs):
        retVal = super(Program, self).__init__(*args, **kwargs)
        
        for type in ['teach','learn','manage','onsite']:
            setattr(self, 'get_%s_url' % type, self._get_type_url(type))

        return retVal

    def save(self):
        
        retVal = super(Program, self).save()
        
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
        from esp.users.models import User
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
            students_count = User.objects.filter(students_dict['classreg']).count()
        else:
            students_count = 0
            for c in self.classes():
                students_count += c.num_students(use_cache=True)

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
            return self.getResources().filter(res_type=ResourceType.get_or_create('Classroom'))
    
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
            
        for c in result:
            result[c].timegroup = Event.collapse(result[c].timeslots)
        
        return result
    
    def classroom_group_key(self):
        return 'program__groupedclassrooms:%d' % self.id
    
    def clear_classroom_cache(self):
        from django.core.cache import cache
        
        cache_key = classroom_group_key(self)
        cache.delete(cache_key)
    
    def groupedClassrooms(self):
        from esp.resources.models import ResourceType
        from django.core.cache import cache
        
        cache_key = self.classroom_group_key()
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        classrooms = self.getResources().filter(res_type=ResourceType.get_or_create('Classroom')).order_by('event')
        
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
        return Class.objects.filter(parent_program = self).order_by('id')        

    def getTimeSlots(self):
        return Event.objects.filter(anchor=self.anchor).order_by('start')

    def getResourceTypes(self):
        #   Show all resources pertaining to the program that aren't these two hidden ones.
        from esp.resources.models import ResourceType
        exclude_types = [ResourceType.get_or_create('Classroom'), ResourceType.get_or_create('Teacher Availability')]
        return ResourceType.objects.filter(Q(program=self) | Q(program__isnull=True)).exclude(id__in=[t.id for t in exclude_types])

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

    def getDurations(self):
        """ Find all contiguous time blocks and provide a list of duration options. """
        times = Event.group_contiguous(list(self.getTimeSlots()))

        durationDict = {}
        
        #   I hope this isn't too terribly slow... not bothering with a faster way
        for t_list in times:
            n = len(t_list)
            for i in range(0, n):
                for j in range(i, n):
                    time_option = t_list[j].end - t_list[i].start
                    durationSeconds = time_option.seconds
                    durationDict[durationSeconds / 3600.0] = \
                                        str(durationSeconds / 3600) + ':' + \
                                        str((durationSeconds / 60) % 60).rjust(2,'0')
            
        durationList = durationDict.items()

        return durationList

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
    picture = models.ImageField(height_field = 'picture_height', width_field = 'picture_width', upload_to = "uploaded/bio_pictures/%y_%m/",blank=True, null=True)
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

    household_income = models.CharField(verbose_name = 'Approximately what is your household income (round to the nearest $10,000)?', null=True, blank=True,
                        maxlength=12)

    extra_explaination = models.TextField(verbose_name = 'Please describe in detail your financial situation this year', null=True, blank=True)

    student_prepare = models.BooleanField(verbose_name = 'Did anyone besides the student fill out any portions of this form?', blank=True,null=True)

    done = models.BooleanField(default=False, editable=False)

    reviewed = models.BooleanField(default=False, editable=False, verbose_name='Reviewed by Directors')

    amount_received = models.IntegerField(blank=True,null=True, editable=False, verbose_name='Amount granted')
    amount_needed = models.IntegerField(blank=True,null=True, editable=False, verbose_name='Amount due from student')

    def __str__(self):
        """ Represent this as a string. """
        accepted_verb = GetNode('V/Flags/Registration/Accepted')
        num_classes = UserBit.find_by_anchor_perms(Class, self.user, accepted_verb).filter(parent_program = self.program).count()

        string = "Financial Aid Application for %s (enrolled in %s classes)"%\
                 (ESPUser(self.user).name(), num_classes)

        if self.done:
            string = "Finished " + string

        if self.reviewed:
            string += " (reviewed)"

        return string

    class Admin:
        pass

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
    
    def __str__(self):
        return str(self.user)

    class Admin:
        pass

from esp.program.models.class_ import *
