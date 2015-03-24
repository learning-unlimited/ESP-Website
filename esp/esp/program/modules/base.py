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
""" This module houses the base ProgramModuleObj from which all module handlers are derived.
    There are many useful and magical functions provided in here, most of which can be called
    from within the program handler.
"""
from functools import wraps

from django.db import models
from django.utils.decorators import available_attrs
from django.utils.safestring import mark_safe

from esp.program.models import Program, ProgramModule
from esp.users.models import ESPUser, Permission
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

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

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

    def docs(self):
        if hasattr(self, 'doc') and self.doc is not None and str(self.doc).strip() != '':
            return self.doc
        return self.module.link_title

    def __unicode__(self):
        return '"%s" for "%s"' % (self.module.admin_title, str(self.program))

    def get_program(self):
        """ Backward compatibility; see ClassRegModuleInfo.get_program """
        return self.program

    def get_views_by_call_tag(self, tags):
        """ We define decorators below (aux_call, main_call, etc.) which allow
            methods within the ProgramModuleObj subclass to be tagged with
            metadata.  At the moment, this metadata is a string stored in the
            'call_tag' attribute.  This function searches the methods of the
            current program module to find those that match the list supplied
            in the 'tags' argument. """
        from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
            
        result = []
        
        #   Filter out attributes that we don't want to look at: 
        #   - Attributes of ProgramMdouleObj, including Django stuff
        #   - Module extension attributes
        key_set = set(dir(self)) - set(dir(ProgramModuleObj)) - set(self.__class__._meta.get_all_field_names())
        for exclude_class in [ClassRegModuleInfo, StudentClassRegModuleInfo]:
            key_set = filter(lambda key: key not in dir(exclude_class), key_set)
        for key in key_set:
            #   Fetch the attribute, now that we're confident it's safe to look at.
            item = getattr(self, key)
            #   This is a hack to test whether the item is a bound method,
            #   maybe there is a better way.
            if isinstance(item, type(self.get_views_by_call_tag)) and hasattr(item, 'call_tag'):
                if item.call_tag in tags:
                    result.append(key)
            
        return result
    
    def get_main_view(self, tl=None):
        if tl or not hasattr(self, '_main_view'):
            main_views = self.get_views_by_call_tag(['Main Call'])
        if tl:
            tl_matching_views = filter(lambda x: hasattr(getattr(self, x), 'call_tl') and getattr(self, x).call_tl == tl, main_views)
            if len(tl_matching_views) > 0:
                return tl_matching_views[0]
        if not hasattr(self, '_main_view'):
            if len(main_views) > 0:
                self._main_view = main_views[0]
            else:
                self._main_view = None
        return self._main_view
    main_view = property(get_main_view)
    
    def main_view_fn(self, request, tl, one, two, call_txt, extra, prog):
        return getattr(self, self.get_main_view(tl))(request, tl, one, two, call_txt, extra, prog)
    
    def get_all_views(self):
        if not hasattr(self, '_views'):
            self._views = self.get_views_by_call_tag(['Main Call', 'Aux Call'])
        return self._views
    views = property(get_all_views)
    
    def get_msg_vars(self, user, key):
        return None

    def getCoreView(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(get_current_request().user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                return getattr(module, module.get_main_view(tl))
        assert False, 'No core module to return to!'

    def getCoreURL(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(get_current_request().user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                 return '/'+tl+'/'+self.program.getUrlBase()+'/'+module.get_main_view(tl)

    def goToCore(self, tl):
        return HttpResponseRedirect(self.getCoreURL(tl))

    def getQForUser(self, QRestriction):
        # Let's not do anything and say we did...
        return QRestriction

    @cache_function
    def findModuleObject(tl, call_txt, prog):
        """ This function caches the customized (augmented) program module object
            matching a particular view function and area. """
        #   Check for a module that has a matching main_call
        main_call_map = prog.getModuleViews(main_only=True)
        if (tl, call_txt) in main_call_map:
            return main_call_map[(tl, call_txt)]
            
        #   Check for a module that has a matching aux_call
        all_call_map = prog.getModuleViews(main_only=False)
        if (tl, call_txt) in all_call_map:
            return all_call_map[(tl, call_txt)]
            
        #   If no module matched those criteria, we are looking for a page that does not exist.
        raise Http404
        
    #   Program.getModules cache takes care of our dependencies
    findModuleObject.depend_on_cache(Program.getModules_cached, lambda **kwargs: {})
    findModuleObject = staticmethod(findModuleObject)
    
    #   The list of modules in a particular category (student reg, teacher reg)
    #   is accessed frequently and should be cached.
    @cache_function
    def findCategoryModules(self, include_optional):
        prog = self.program
        module_type = self.module.module_type
        moduleobjs = filter(lambda mod: mod.module.module_type == module_type, prog.getModules())
        if not include_optional:
            moduleobjs = filter(lambda mod: mod.required == True, moduleobjs)
        moduleobjs.sort(key=lambda mod: mod.seq)
        return moduleobjs
    #   Program.getModules cache takes care of our dependencies
    findCategoryModules.depend_on_cache(Program.getModules_cached, lambda **kwargs: {})
    
    @staticmethod
    def findModule(request, tl, one, two, call_txt, extra, prog):
        moduleobj = ProgramModuleObj.findModuleObject(tl, call_txt, prog)

        #   If a "core" module has been found:
        #   Put the user through a sequence of all required modules in the same category.
        #   Only do so if we've not blocked this behavior, though
        if tl not in ["manage", "json", "volunteer"] and isinstance(moduleobj, CoreModule):
            scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
            if scrmi.force_show_required_modules:
                if not_logged_in(request):
                    return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
                other_modules = moduleobj.findCategoryModules(False)
                for m in other_modules:
                    m.request = request
                    if not isinstance(m, CoreModule) and not m.isCompleted() and m.main_view:
                        return m.main_view_fn(request, tl, one, two, call_txt, extra, prog)

        #   If the module isn't "core" or the user did all required steps,
        #   call on the originally requested view.
        moduleobj.request = request
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
        
        classes = ClassSubject.objects.filter(id = clsid, parent_program = self.program)
            
        if len(classes) == 1:
            if not get_current_request().user.canEdit(classes[0]):
                from esp.middleware import ESPError
                message = 'You do not have permission to edit %s.' % classes[0].title
                raise ESPError(message, log=False)
            else:
                Found = True
                return (classes[0], True)
        return (False, False)
            

    def baseDir(self):
        return 'program/modules/'+self.__class__.__name__.lower()+'/'

    def fixExtensions(self):
        """ Find module extensions that this program module inherits from, and 
        incorporate those into its attributes. """
        
        self._ext_map = {}
        if self.program:
            for key, x in self.extensions().items():
                ext = self.program.getModuleExtension(x, module_id=self.id)
                setattr(self, key, ext)
                for attr in dir(ext):
                    self._ext_map[attr] = key

    def __getattr__(self, attr):
        # backward compatibility
        if hasattr(self, '_ext_map') and self._ext_map.has_key(attr):
            key = self._ext_map[attr]
            ext = getattr(self, key)
            import warnings
            warnings.warn('Direct access of module extension attributes from module objects is deprecated. Use <module>.%s.%s instead.' % (key, attr), DeprecationWarning, stacklevel=2)
            return getattr(ext, attr)
        raise AttributeError('%r object has no attribute %r' % (self.__class__, attr))

    def deadline_met(self, extension=''):
    
        #   Short-circuit the request middleware during testing, when we call
        #   this function without an actual request.
        if hasattr(self, 'user'):
            user = self.user
        else:
            request = get_current_request()
            user = request.user

        if not user or not self.program:
            raise ESPError(False), "There is no user or program object!"

        if self.module.module_type != 'learn' and self.module.module_type != 'teach':
            return True
            
        canView = user.isOnsite(self.program) or user.isAdministrator(self.program)

        if not canView:
            deadline = {'learn':'Student', 'teach':'Teacher'}[self.module.module_type]+extension
            canView = Permission.user_has_perm(user, deadline, program=self.program)

        return canView

    # important functions for hooks...
    @cache_function
    def get_full_path(self, tl=None):
        return '/' + self.module.module_type + '/' + self.program.url + '/' + self.get_main_view(tl)
    get_full_path.depend_on_row('modules.ProgramModuleObj', 'self')

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
                (self.get_full_path(tl=self.module.module_type), self.module.link_title, self.module.link_title)
        else:
            link = u'<a href="%s" title="%s" onmouseover="updateDocs(\'<p>%s</p>\');" class="vModuleLink" >%s</a>' % \
               (self.get_full_path('manage'), self.module.link_title, self.docs().replace("'", "\\'").replace('\n','<br />\\n').replace('\r', ''), self.module.link_title)

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
        return (not self.main_view)

    def isCompleted(self):
        return False

    def prepare(self, context):
        return context

    def getNavBars(self):
        return []

    def getTemplate(self):
        if self.module.inline_template:
            baseDir = 'program/modules/'+self.__class__.__name__.lower()+'/'
            base_template = baseDir + self.module.inline_template
            per_program_template = baseDir+'per_program/'+str(self.program.id)+ \
                '_'+ self.module.inline_template

            #   Iterate over a bunch of reasons to return a template;
            #   if none of them come up true, return None.
            try:
                get_template(per_program_template)
                if self.useTemplate():
                    return per_program_template
            except TemplateDoesNotExist:
                try:
                    get_template(base_template)
                    if self.useTemplate():
                        return base_template
                except TemplateDoesNotExist:
                    pass
            
            return 'program/modules/%s/%s' % (self.__class__.__name__.lower(), self.module.inline_template)

        return None

    def teachers(self, QObject = False):
        return {}

    def studentDesc(self):
        return {}

    def teacherDesc(self):
        return {}

    def students(self,QObject=False):
        return {}
        
    def volunteerDesc(self):
        return {}

    def volunteers(self,QObject=False):
        return {}

    def isStep(self):
        return True

    @classmethod
    def extensions(cls):
        return {}

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
        """

        props = cls.module_properties()

        def update_props(props):
            if not "handler" in props:
                props["handler"] = cls.__name__
            if not "admin_title" in props:
                props["admin_title"] = "%(link_title)s (%(handler)s)" % props
            if not "seq" in props:
                props["seq"] = 200

        if isinstance(props, dict):
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
def not_logged_in(request):
    return (not request.user or not request.user.is_authenticated() or not request.user.id)

def usercheck_usetl(method):
    def _checkUser(moduleObj, request, tl, *args, **kwargs):
        errorpage = 'errors/program/nota'+tl+'.html'
    
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if ((not request.user.isAdmin(moduleObj.program))
             and (
                 (tl == 'learn' and not request.user.isStudent())
                 or (tl == 'teach' and not request.user.isTeacher())
                 or (tl == 'manage'))):
            return render_to_response(errorpage, request, {})

        return method(moduleObj, request, tl, *args, **kwargs)

    return _checkUser


def needs_teacher(method):
    def _checkTeacher(moduleObj, request, *args, **kwargs):
        allowed_teacher_types = Tag.getTag("allowed_teacher_types", moduleObj.program, default='').split(",")
        
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
            
        if not request.user.isTeacher() and not request.user.isAdmin(moduleObj.program) and not (set(request.user.getUserTypes()) & set(allowed_teacher_types)):
            return render_to_response('errors/program/notateacher.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkTeacher.call_tl = 'teach'
    _checkTeacher.method = method
    return _checkTeacher

def needs_admin(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if request.session.has_key('user_morph'):
            morpheduser=ESPUser.objects.get(id=request.session['user_morph']['olduser_id'])
        else:
            morpheduser=None
            
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not (request.user.isAdmin(moduleObj.program) or (morpheduser and morpheduser.isAdmin(moduleObj.program))):
            if not ( hasattr(request.user, 'other_user') and request.user.other_user and request.user.other_user.isAdmin(moduleObj.program) ):
                return render_to_response('errors/program/notanadmin.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkAdmin.call_tl = 'manage'
    _checkAdmin.method = method
    return _checkAdmin

def needs_onsite(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not request.user.isOnsite(moduleObj.program) and not request.user.isAdmin(moduleObj.program):
            user = request.user
            user = ESPUser(user)
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, {})
            user.switch_back(request)
        return method(moduleObj, request, *args, **kwargs)
    _checkAdmin.call_tl = 'onsite'
    _checkAdmin.method = method
    return _checkAdmin

def needs_onsite_no_switchback(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not request.user.isOnsite(moduleObj.program) and not request.user.isAdmin(moduleObj.program):
            user = request.user
            user = ESPUser(user)
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkAdmin.call_tl = 'onsite'
    _checkAdmin.method = method
    return _checkAdmin

def needs_student(method):
    def _checkStudent(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        if not request.user.isStudent() and not request.user.isAdmin(moduleObj.program):
            allowed_student_types = Tag.getTag("allowed_student_types", moduleObj.program, default='')
            matching_user_types = any(x in request.user.groups.all().values_list("name",flat=True) for x in allowed_student_types.split(","))
            if not matching_user_types:
                return render_to_response('errors/program/notastudent.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkStudent.call_tl = 'learn'
    _checkStudent.method = method
    return _checkStudent        

def needs_account(method):
    def _checkAccount(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
            
        return method(moduleObj, request, *args, **kwargs)
    _checkAccount.method = method
    return _checkAccount

def meets_grade(method):
    def _checkGrade(moduleObj, request, tl, *args, **kwargs):
        errorpage = 'errors/program/wronggrade.html'

        # if there's grade override we can just skip everything
        if Permission.user_has_perm(request.user, 'GradeOverride', moduleObj.program):
            return method(moduleObj, request, tl, *args, **kwargs)
        
        # now we have to use the grade..

        # get the last grade...
        cur_grade = request.user.getGrade(moduleObj.program)
        if cur_grade != 0 and (cur_grade < moduleObj.program.grade_min or \
                               cur_grade > moduleObj.program.grade_max):
            return render_to_response(errorpage, request, {'yog': request.user.getYOG(moduleObj.program)})

        return method(moduleObj, request, tl, *args, **kwargs)
    
    return _checkGrade

# Anything you can do, I can do meta

# Just broke out this function to allow combined deadlines (see meets_any_deadline,
# meets_all_deadlines functions below).  -Michael P, 6/23/2009
def _checkDeadline_helper(method, extension, moduleObj, request, tl, *args, **kwargs):
    if tl != 'learn' and tl != 'teach':
        return (True, None)
    response = None
    canView = False
    if not_logged_in(request):
        response = HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
    else:
        canView = request.user.updateOnsite(request)
        if not canView:
            perm_name = {'learn':'Student','teach':'Teacher'}[tl]+extension
            canView = Permission.user_has_perm(request.user, 
                                               perm_name,
                                               program=request.program)
            #   For now, allow an exception if the user is of the wrong type
            #   This is because we are used to UserBits having a null user affecting everyone, regardless of user type.
            if not canView and Permission.valid_objects().filter(permission_type=perm_name, program=request.program, user__isnull=True).exists():
                canView = True

    return (canView, response)

def list_extensions(tl, extensions, andor=''):
    nicetl={'teach':'Teacher','learn':'Student'}[tl]
    if len(extensions)==0:
        return 'no deadlines were'
    elif len(extensions)==1:
        return 'the deadline '+nicetl+extensions[0]+' was'
    elif len(extensions)==2:
        return 'the deadlines '+nicetl+extensions[0]+' '+andor+' '+nicetl+extensions[1]+' were'
    else:
        return 'the deadlines '+', '.join([nicetl+e for e in extensions[:-1]])+', '+andor+' '+nicetl+extensions[-1]+' were'

#   Return a decorator that returns a function calling the decorated function if
#   the deadline is met, or a function that generates an error page if the
#   deadline is not met.
def meets_deadline(extension=''):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            (canView, response) = _checkDeadline_helper(method, extension, moduleObj, request, tl, *args, **kwargs)
            if canView:
                return method(moduleObj, request, tl, *args, **kwargs)
            else:
                if response:
                    return response
                else:
                    return render_to_response(errorpage, request, {'extension': list_extensions(tl,[extension]), 'moduleObj': moduleObj})
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
                (canView, response) = _checkDeadline_helper(method, ext, moduleObj, request, tl, *args, **kwargs)
                if canView:
                    return method(moduleObj, request, tl, *args, **kwargs)
            if response:
                return response
            else:
                return render_to_response(errorpage, request, {'extension': list_extensions(tl,extensions,'and') , 'moduleObj': moduleObj})
        return _checkDeadline
    return meets_deadline

#   Line meets_any_deadline above, but requires that all deadlines are met.
def meets_all_deadlines(extensions=[]):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            for ext in extensions:
                (canView, response) = _checkDeadline_helper(method, ext, moduleObj, request, tl, *args, **kwargs)
                if not canView:
                    if response:
                        return response
                    else:
                        return render_to_response(errorpage, request, {'extension': list_extensions(tl,extensions,'or') , 'moduleObj': moduleObj})
            return method(moduleObj, request, tl, *args, **kwargs)
        return _checkDeadline
    return meets_deadline

def user_passes_test(test_func, error_message):
    """A method decorator based on django.contrib.auth.decorators.user_passes_test.

    Decorate a ProgramModuleObj view method, such that requests will only
    pass through if test_func(moduleObj) returns True. test_func must be a
    callable with a signature of test_func(moduleObj) -> `bool`.
    The body of test_func can use moduleObj and get_current_request()
    (particularly, get_current_request().user) to decide if it should return
    True or False.

    In the failure case, an error page will be rendered. error_message will
    be used as the 'extension' template variable in the error page, so it
    should be formatted similarly to the output of list_extensions().
    """
    def user_passes_test(view_method):
        @wraps(view_method, assigned=available_attrs(view_method))
        def _check(moduleObj, request, tl, *args, **kwargs):
            if test_func(moduleObj):
                return view_method(moduleObj, request, tl, *args, **kwargs)
            errorpage = 'errors/program/deadline-%s.html' % tl
            return render_to_response(
                errorpage,
                request,
                {'extension': error_message, 'moduleObj': moduleObj},
            )
        return _check
    return user_passes_test


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
