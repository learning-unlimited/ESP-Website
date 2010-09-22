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
""" This module houses the base ProgramModuleObj from which all module handlers are derived.
    There are many useful and magical functions provided in here, most of which can be called
    from within the program handler.
"""

from django.db import models
from django.utils.safestring import mark_safe

from esp.program.models import Program, ProgramModule
from esp.users.models import ESPUser, UserBit
from esp.datatree.models import GetNode
from esp.web.util import render_to_response
from esp.cache import cache_function
from esp.tagdict.models import Tag
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from urllib import quote
from django.db.models.query import Q
from django.core.cache import cache
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

from os.path import exists

LOGIN_URL = settings.LOGIN_URL

class CoreModule(object):
    """
    All core modules should derive from this.
    """
    pass

class ProgramModuleObj(models.Model):
    program  = models.ForeignKey(Program)
    module   = models.ForeignKey(ProgramModule)
    seq      = models.IntegerField()
    required = models.BooleanField()
    required_label = models.CharField(max_length=80, blank=True, null=True)
        
    def program_anchor_cached(self, parent=False):
        """ We reference "self.program.anchor" quite often.  Getting it requires two DB lookups.  So, cache it. """
        CACHE_KEY = "PROGRAMMODULEOBJ__PROGRAM__ANCHOR__CACHE__%d,%d" % ((parent and 1 or 0), self.id)
        val = cache.get(CACHE_KEY)
        if val == None:
            if parent and self.program.getParentProgram():
                val = self.program.getParentProgram().anchor
            else:
                val = self.program.anchor
            cache.set(CACHE_KEY, val, 60)

        return val

    def docs(self):
        if hasattr(self, 'doc') and self.doc is not None and str(self.doc).strip() != '':
            return self.doc
        return self.module.link_title

    def __unicode__(self):
        return '"%s" for "%s"' % (self.module.admin_title, str(self.program))

    def all_views(self):
        if self.module and self.module.aux_calls:
            return self.module.aux_calls.strip(',').split(',')

        return []

    def get_msg_vars(self, user, key):
        return None

    def getCoreView(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(self.user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                return getattr(module, module.module.main_call)
        assert False, 'No core module to return to!'

    def getCoreURL(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(self.user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                 return '/'+tl+'/'+self.program.getUrlBase()+'/'+module.module.main_call


    def goToCore(self, tl):
        return HttpResponseRedirect(self.getCoreURL(tl))

    def getQForUser(self, QRestriction):
        # Let's not do anything and say we did...
        return QRestriction
    
        from esp.users.models import User
        ids = [ x['id'] for x in User.objects.filter(QRestriction).values('id')]
        if len(ids) == 0:
            return Q(id = -1)
        else:
            return Q(id__in = ids)

    @staticmethod
    def renderMyESP():
        """
        Returns a rendered myESP home template, with content from all relevant modules

        Renders the page based on content from all 
        """
        all_modules = []
        context = {}

        for x in ProgramModules.objects.all():
            try:
                thisClass = x.getPythonClass()

                try:
                    page = thisClass.summaryPage()
                    context = thisClass.prepareSummary(context)
                except:
                    page = None

                
                    subpages = [ { 'name': i.__name__, 'link_title': i.__doc__.split('\n')[0], 'function': i } for i in thisClass.getSummaryCalls() ]
                    if subpages == []:
                        subpages = None

               
                    all_modules.append({ 'module': thisClass,
                                         'page': page,
                                         'subpages': subpages })
            except:
                pass

        context['modules'] = all_modules
        return render_to_response("myesp/mainpage.html", context)
            
    #   This function caches the customized (augmented) program module objects
    @cache_function
    def findModuleObject(tl, call_txt, prog):
        # Make sure all modules exist
        modules = prog.program_modules.all()
        for module in modules:
            ProgramModuleObj.getFromProgModule(prog, module)

        modules = ProgramModule.objects.filter(main_call = call_txt, module_type = tl).select_related()[:1]
        module = None

        if len(modules) == 0:
            modules = ProgramModule.objects.filter(aux_calls__contains = call_txt, module_type = tl).select_related()
            for module in modules:
                if call_txt in module.aux_calls.strip().split(','):
                    return ProgramModuleObj.getFromProgModule(prog, module)
        else:
            module = modules[0]
            return ProgramModuleObj.getFromProgModule(prog, module)

        raise Http404
        
    #   Invalidate cache when any program module related data is saved
    #   Technically this should include the options (StudentClassRegModuleInfo, etc.)
    findModuleObject.depend_on_model(lambda: ProgramModule)
    findModuleObject.depend_on_model(lambda: ProgramModuleObj)
    findModuleObject = staticmethod(findModuleObject)
    
    #   The list of modules in a particular category (student reg, teacher reg)
    #   is accessed frequently and should be cached.
    @cache_function
    def findCategoryModules(self, include_optional):
        prog = self.program
        module_type = self.module.module_type

        if not include_optional:
            other_modules = ProgramModuleObj.objects.filter(program=prog, module__module_type=module_type, required=True).select_related(depth=1).order_by('seq')
        else:
            other_modules = ProgramModuleObj.objects.filter(program=prog, module__module_type=module_type).select_related(depth=1).order_by('seq')
        
        result_modules = list(other_modules)
        for mod in result_modules:
            mod.__class__ = mod.module.getPythonClass()
            
        return result_modules
        
    findCategoryModules.depend_on_model(lambda: ProgramModule)
    findCategoryModules.depend_on_model(lambda: ProgramModuleObj)
    
    @staticmethod
    def findModule(request, tl, one, two, call_txt, extra, prog):
        moduleobj = ProgramModuleObj.findModuleObject(tl, call_txt, prog)
        user = ESPUser(request.user)
        scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')

        #   If a "core" module has been found:
        #   Put the user through a sequence of all required modules in the same category.
        #   Only do so if we've not blocked this behavior, though
        if scrmi.force_show_required_modules:
            if tl != "manage" and request.user.is_authenticated() and isinstance(moduleobj, CoreModule):
                other_modules = moduleobj.findCategoryModules(False)
                for m in other_modules:
                    m.request = request
                    m.user    = user
                    if not isinstance(m, CoreModule) and not m.isCompleted() and hasattr(m, m.module.main_call):
                        return getattr(m, m.module.main_call)(request, tl, one, two, call_txt, extra, prog)

        #   If the module isn't "core" or the user did all required steps,
        #   call on the originally requested view.
        moduleobj.request = request
        moduleobj.user    = user
        if hasattr(moduleobj, call_txt):
            return getattr(moduleobj, call_txt)(request, tl, one, two, call_txt, extra, prog)

        raise Http404

    @staticmethod
    def getFromProgModule(prog, mod):
        import esp.program.modules.models
        """ Return an appropriate module object for a Module and a Program.
           Note that all the data is forcibly taken from the ProgramModuleObj table """
        
        BaseModuleList = ProgramModuleObj.objects.filter(program = prog, module = mod).select_related('module')
        if len(BaseModuleList) < 1:
            BaseModule = ProgramModuleObj()
            BaseModule.program = prog
            BaseModule.module  = mod
            BaseModule.seq     = mod.seq
            BaseModule.required = mod.required
            BaseModule.save()

        elif len(BaseModuleList) > 1:
            assert False, 'Too many module objects!'
        else:
            BaseModule = BaseModuleList[0]
        
        ModuleObj   = mod.getPythonClass()()
        ModuleObj.__dict__.update(BaseModule.__dict__)
        ModuleObj.fixExtensions()

        return ModuleObj



    def getClassFromId(self, clsid, tl='teach'):
        """ This function can be called from a view to get a class object from an id. The id can be given
            with request or extra, but it will try to get it in any way. """

        from esp.program.models import ClassSubject

        classes = []
        try:
            clsid = int(clsid)
        except:
            return (False, True)
        
        classes = ClassSubject.objects.filter(id = clsid)
            
        if len(classes) == 1:
            if not self.user.canEdit(classes[0]):
                from esp.middleware import ESPError
                raise ESPError(False), 'You do not have permission to edit %s.' %\
                      classes[0].title()
            else:
                Found = True
                return (classes[0], True)
        return (False, False)
            

    def baseDir(self):
        return 'program/modules/'+self.__class__.__name__.lower()+'/'

    def fixExtensions(self):
        """ Find module extensions that this program module inherits from, and 
        incorporate those into its attributes. """
        
        old_id = self.id
        old_module = self.module
        if self.program:
            for x in self._meta.parents:
                if x != ProgramModuleObj:
                    new_dict = self.program.getModuleExtension(x, module_id=old_id).__dict__
                    self.__dict__.update(new_dict)
            self.id = old_id
            self.module = old_module

    def deadline_met(self, extension=''):
    
        from esp.users.models import UserBit
        from esp.datatree.models import GetNode, DataTree

        if not self.user or not self.program:
            raise ESPError(False), "There is no user or program object!"


            
        if self.module.module_type != 'learn' and self.module.module_type != 'teach':
            return True

        canView = False

        if self.user.__dict__.has_key('onsite_local'):
            canView = self.user.__dict__['onsite_local']

        if not canView:
            test_node = GetNode('V/Deadline/Registration/'+{'learn':'Student', 'teach':'Teacher'}[self.module.module_type]+extension)
            canView = UserBit.UserHasPerms(self.user, self.program.anchor_id, test_node)

        return canView

    # important functions for hooks...
    @cache_function
    def get_full_path(self):
        str_array = self.program.anchor.tree_encode()
        url = '/'+self.module.module_type \
              +'/'+'/'.join(str_array[-2:])+'/'+self.module.main_call
        return url
    get_full_path.depend_on_row(lambda: ProgramModuleObj, 'self')

    @classmethod
    def get_summary_path(cls, function):
        """
        Returns the base url of a view function

        'function' must be a member of 'cls'.  Both 'cls' and 'function' must
        not be anonymous (ie., they musht have __name__ defined).
        """
        
        url = '/myesp/modules/' + cls.__name__ + '/' + function.__name__
        return url
    
    def setUser(self, user):
        self.user = user
        self.curUser = user

    
    def makeLink(self):
        if not self.module.module_type == 'manage':
            link = u'<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
                (self.get_full_path(), self.module.link_title, self.module.link_title)
        else:
            link = u'<a href="%s" title="%s" onmouseover="updateDocs(\'<p>%s</p>\');" class="vModuleLink" >%s</a>' % \
               (self.get_full_path(), self.module.link_title, self.docs().replace("'", "\\'").replace('\n','<br />\\n').replace('\r', ''), self.module.link_title)

        return mark_safe(link)


    @classmethod
    def makeSummaryLink(cls, function):
        """
        Makes a nice HTML link that points to the specified view function, as a member of 'cls'

        'function' must be a member function of 'cls'; 'cls' must be a valid program module class.  Both must be non-anonymous; ie., __name__ must be definned for both.
        """
        try:
            function_pretty_name = function.__doc__.split('\n')[0]
        except AttributeError: # Someone forgot to define a docstring!
            function_pretty_name = "[%s.%s]" % (cls.__name__, function.__name__)        

        return '<a href="%s" class="vModuleLink" onmouseover="updateDocs(\'<p>%s</p>\')">%s</a>' % \
               (cls.get_summary_path(function), function.__doc__, function_pretty_name, )

    def useTemplate(self):
        """ Use a template if the `mainView' function doesn't exist. """
        return (not self.module.main_call) or (not hasattr(self, self.module.main_call))

    def isCompleted(self):
        return False

    def prepare(self, context):
        return context

    def getNavBars(self):
        return []

    def getTemplate(self):
        baseDir = 'program/modules/'+self.__class__.__name__.lower()+'/'
        mainCallTemp = self.module.main_call+'.html'

        per_program_template = baseDir+'per_program/'+str(self.program.id)+ \
            '_'+ mainCallTemp

        try:
            get_template(per_program_template)
            return per_program_template
        except TemplateDoesNotExist:
            return baseDir + mainCallTemp
                

    def teachers(self, QObject = False):
        return {}

    def studentDesc(self):
        return {}

    def teacherDesc(self):
        return {}

    def students(self,QObject=False):
        return {}

    def isStep(self):
        return True

    def extensions(self):
        return []

    @classmethod
    def module_properties(cls):
        """
        Specify the properties of the ProgramModule row corresponding
        to this table.
        This function should return a dictionary with keys matching
        the field names of the ProgramModule table, with at least
        "link_title" and "module_type".
        """
        return []

    @classmethod
    def module_properties_autopopulated(cls):
        """
        Return a dictionary of the ProgramModule properties of this class.
        The dictionary will return the same dictionary as
        self.module_properties(), with the following values added if their
        corresponding keys don't already exist:
        - "handler"
        - "admin_title" (as "%(link_title)s (%(handler)s)")
        - "seq" (as 200)
        - "aux_calls" (based on @aux_calls decorators)
        - "main_call" (based on the @main_call decorator)
        """

        props = cls.module_properties()

        
        def update_props(props):
            if not "handler" in props:
                props["handler"] = cls.__name__
            if not "admin_title" in props:
                props["admin_title"] = "%(link_title)s (%(handler)s)" % props
            if not "seq" in props:
                props["seq"] = 200

            if not "aux_calls" in props:
                NAME = 0
                FN = 1
                props["aux_calls"] = ",".join( [ x[NAME] for x in cls.__dict__.items()
                                                 if getattr(x[FN], "call_tag", None) == "Aux Call" ] )

            if not "main_call" in props:
                NAME = 0
                FN = 1
                mainCallList = [ x[NAME] for x in cls.__dict__.items()
                                 if getattr(x[FN], "call_tag", None) == "Main Call" ]
                assert len(mainCallList) <= 1, "Error: You can only have one Main Call per class!: (%s: %s)" % (cls.__name__, ",".join(mainCallList))
                props["main_call"] = ",".join(mainCallList)
            
        if type(props) == dict:
            props = [ props ]

        for prop in props:
            update_props(prop)
            
        return props
                
        
            
    @classmethod
    def getSummary(cls):
        """
        Return  the name of a template file that renders the myESP view for this class.
        Returns None if no such view exists for this class.

        This is a stub, to be overridden by subclasses.
        """
        return None

    @classmethod
    def prepareSummary(cls, context):
        """
        Modifies the 'context' dictionary by adding any data that the template pointed to
        by 'getSummary', needs in its context in order to render proprerly.

        Keys added to 'context' should be strings that contain an identifier that's
        unique to this class, such as self.__name__.  This is not strictly enforced, though.

        Returns the modified context.

        This is a stub, to be overridden by subclasses.
        """
        return context



# will check and depending on the value of tl
# will use .isTeacher or .isStudent()
def usercheck_usetl(method):
    def _checkUser(moduleObj, request, tl, *args, **kwargs):
        errorpage = 'errors/program/nota'+tl+'.html'
    
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        if tl == 'learn' and not moduleObj.user.isStudent():
            return render_to_response(errorpage, request, moduleObj.program, {})
        
        if tl == 'teach' and not moduleObj.user.isTeacher():
            return render_to_response(errorpage, request, moduleObj.program, {})
        
        if tl == 'manage' and not moduleObj.user.isAdmin(moduleObj.program):
            return render_to_response(errorpage, request, moduleObj.program, {})

        return method(moduleObj, request, tl, *args, **kwargs)

    return _checkUser


def needs_teacher(method):
    def _checkTeacher(moduleObj, request, *args, **kwargs):
        allowed_teacher_types = Tag.getTag("allowed_teacher_types", moduleObj.program, default='').split(",")
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        if not moduleObj.user.isTeacher() and not moduleObj.user.isAdmin(moduleObj.program) and not (set(moduleObj.user.getUserTypes()) & set(allowed_teacher_types)):
            return render_to_response('errors/program/notateacher.html', request, (moduleObj.program, 'teach'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkTeacher

def needs_admin(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if request.session.has_key('user_morph'):
            morpheduser=ESPUser.objects.get(id=request.session['user_morph']['olduser_id'])
        else:
            morpheduser=None

        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not (moduleObj.user.isAdmin(moduleObj.program) or (morpheduser and morpheduser.isAdmin(moduleObj.program))):
            if not ( hasattr(moduleObj.user, 'other_user') and moduleObj.user.other_user and moduleObj.user.other_user.isAdmin(moduleObj.program) ):
                return render_to_response('errors/program/notanadmin.html', request, (moduleObj.program, 'manage'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkAdmin

def needs_onsite(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isOnsite(moduleObj.program) and not moduleObj.user.isAdmin(moduleObj.program):
            user = moduleObj.user
            user = ESPUser(user)
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, (moduleObj.program, 'onsite'), {})
            user.switch_back(request)
        return method(moduleObj, request, *args, **kwargs)

    return _checkAdmin

def needs_onsite_no_switchback(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isOnsite(moduleObj.program) and not moduleObj.user.isAdmin(moduleObj.program):
            user = moduleObj.user
            user = ESPUser(user)
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, (moduleObj.program, 'onsite'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkAdmin

def needs_student(method):
    def _checkStudent(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isStudent() and not moduleObj.user.isAdmin(moduleObj.program):
            allowed_student_types = Tag.getTag("allowed_student_types", moduleObj.program, default='')
            matching_user_types = UserBit.valid_objects().filter(user=moduleObj.user, verb__parent=GetNode("V/Flags/UserRole"), verb__name__in=allowed_student_types.split(","))
            if not matching_user_types:
                return render_to_response('errors/program/notastudent.html', request, (moduleObj.program, 'learn'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkStudent        


def meets_grade(method):
    def _checkGrade(moduleObj, request, tl, *args, **kwargs):
        errorpage = 'errors/program/wronggrade.html'
        from esp.datatree.models import DataTree, GetNode, QTree, get_lowest_parent, StringToPerm, PermToString
        from esp.users.models import UserBit

        verb_override = GetNode('V/Flags/Registration/GradeOverride')

        # if there's grade override we can just skip everything
        if UserBit.UserHasPerms(user = moduleObj.user,
                                  qsc  = moduleObj.program.anchor_id,
                                  verb = verb_override):
            return method(moduleObj, request, tl, *args, **kwargs)
        
        # now we have to use the grade..

        # get the last grade...
        cur_grade = moduleObj.user.getGrade()
        if cur_grade != 0 and (cur_grade < moduleObj.program.grade_min or \
                               cur_grade > moduleObj.program.grade_max):
            return render_to_response(errorpage, request, (moduleObj.program, tl), {})

        return method(moduleObj, request, tl, *args, **kwargs)
    
    return _checkGrade

# Anything you can do, I can do meta

# Just broke out this function to allow combined deadlines (see meets_any_deadline,
# meets_all_deadlines functions below).  -Michael P, 6/23/2009
def _checkDeadline_helper(method, extension, moduleObj, request, tl, *args, **kwargs):
    from esp.users.models import UserBit
    from esp.datatree.models import DataTree, GetNode, QTree, get_lowest_parent, StringToPerm, PermToString
    if tl != 'learn' and tl != 'teach':
        return True

    canView = moduleObj.user.updateOnsite(request)
    if not canView:
        canView = UserBit.UserHasPerms(moduleObj.user,
                                       moduleObj.program.anchor_id,
                                       GetNode('V/Deadline/Registration/'+{'learn':'Student',
                                                                       'teach':'Teacher'}[tl]+extension))

    return canView

#   Return a decorator that returns a function calling the decorated function if
#   the deadline is met, or a function that generates an error page if the
#   deadline is not met.
def meets_deadline(extension=''):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            canView = _checkDeadline_helper(method, extension, moduleObj, request, tl, *args, **kwargs)
            if canView:
                return method(moduleObj, request, tl, *args, **kwargs)
            else:
                return render_to_response(errorpage, request, (moduleObj.program, tl), {})
        return _checkDeadline
    return meets_deadline

#   Behaves like the meets_deadline function above, but accepts a list of
#   userbit names.  The returned decorator returns the decorated function if
#   any of the deadlines are met.
def meets_any_deadline(extensions=[]):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            for ext in extensions:
                canView = _checkDeadline_helper(method, ext, moduleObj, request, tl, *args, **kwargs)
                if canView:
                    return method(moduleObj, request, tl, *args, **kwargs)
            return render_to_response(errorpage, request, (moduleObj.program, tl), {})
        return _checkDeadline
    return meets_deadline

#   Line meets_any_deadline above, but requires that all deadlines are met.
def meets_all_deadlines(extensions=[]):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            for ext in extensions:
                canView = _checkDeadline_helper(method, ext, moduleObj, request, tl, *args, **kwargs)
                if not canView:
                    return render_to_response(errorpage, request, (moduleObj.program, tl), {})
            return method(moduleObj, request, tl, *args, **kwargs)
        return _checkDeadline
    return meets_deadline


def main_call(func):
    """
    Tag decorator that flags 'func' as a 'Main Call' function for
    a ProgramModuleObj.
    Note that there must be no more than 1 Main Call per ProgramModuleObj.
    """
    func.call_tag = "Main Call"
    return func

def aux_call(func):
    """
    Tag decorator that flags 'func' as an 'Aux Call' function for
    a ProgramModuleObj.
    """
    func.call_tag = "Aux Call"
    return func
