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
import logging
logger = logging.getLogger(__name__)

from django.db import models
from django.utils.decorators import available_attrs
from django.utils.safestring import mark_safe

from esp.program.models import Program, ProgramModule
from esp.users.models import ESPUser, Permission
from esp.utils.web import render_to_response
from argcache import cache_function
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from urllib import quote
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

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
    required = models.BooleanField(default=False)
    required_label = models.CharField(max_length=80, blank=True, null=False, default="")

    def docs(self):
        if hasattr(self, 'doc') and self.doc is not None and str(self.doc).strip() != '':
            return self.doc
        return self.module.link_title

    def __unicode__(self):
        return '"%s" for "%s"' % (self.module.admin_title, str(self.program))

    def get_views_by_call_tag(self, tags):
        """ We define decorators below (aux_call, main_call, etc.) which allow
            methods within the ProgramModuleObj subclass to be tagged with
            metadata.  At the moment, this metadata is a string stored in the
            'call_tag' attribute.  This function searches the methods of the
            current program module to find those that match the list supplied
            in the 'tags' argument. """
        from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo

        result = []

        #   Filter out attributes that we don't want to look at: attributes of
        #   ProgramModuleObj, including Django stuff
        key_set = set(dir(self)) - set(dir(ProgramModuleObj)) - set(self.__class__._meta.get_fields())
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

    def getCoreURL(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(get_current_request().user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                 return '/'+tl+'/'+self.program.getUrlBase()+'/'+module.get_main_view(tl)

    def goToCore(self, tl):
        return HttpResponseRedirect(self.getCoreURL(tl))

    def require_auth(self):
        return True

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
        from esp.program.modules.handlers.regprofilemodule import RegProfileModule
        moduleobj = ProgramModuleObj.findModuleObject(tl, call_txt, prog)

        #   If a "core" module has been found:
        #   Put the user through a sequence of all required modules in the same category.
        #   Only do so if we've not blocked this behavior, though
        if tl not in ["manage", "json", "volunteer"] and isinstance(moduleobj, CoreModule):
            scrmi = prog.studentclassregmoduleinfo
            if scrmi.force_show_required_modules:
                if not_logged_in(request):
                    return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
                other_modules = moduleobj.findCategoryModules(False)
                for m in other_modules:
                    m.request = request
                    if request.user.updateOnsite(request) and not isinstance(m, RegProfileModule):
                        continue
                    if not isinstance(m, CoreModule) and not m.isCompleted() and m.main_view:
                        return m.main_view_fn(request, tl, one, two, call_txt, extra, prog)

        #   If the module isn't "core" or the user did all required steps,
        #   call on the originally requested view.
        moduleobj.request = request
        if hasattr(moduleobj, call_txt):
            return getattr(moduleobj, call_txt)(request, tl, one, two, call_txt, extra, prog)

        raise Http404

    @staticmethod
    def getFromProgModule(prog, mod, old_prog = None):
        import esp.program.modules.models
        """ Return an appropriate module object for a Module and a Program.
           Note that all the data is forcibly taken from the ProgramModuleObj table """

        BaseModuleList = ProgramModuleObj.objects.filter(program = prog, module = mod).select_related('module')
        if len(BaseModuleList) < 1:
            BaseModule = ProgramModuleObj()
            BaseModule.program = prog
            BaseModule.module = mod
            # If an old program is specified, use the seq and required values from that program
            old_pmo = ProgramModuleObj.objects.filter(program = old_prog, module = mod)
            if len(old_pmo) == 1:
                BaseModule.seq = old_pmo[0].seq
                BaseModule.required = old_pmo[0].required
                BaseModule.required_label = old_pmo[0].required_label
            else:
                BaseModule.seq = mod.seq
                BaseModule.required = mod.required
            BaseModule.save()

        elif len(BaseModuleList) > 1:
            assert False, 'Too many module objects!'
        else:
            BaseModule = BaseModuleList[0]

        ModuleObj   = mod.getPythonClass()()
        ModuleObj.__dict__.update(BaseModule.__dict__)

        return ModuleObj

    def baseDir(self):
        return 'program/modules/'+self.__class__.__name__.lower()+'/'

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

    def useTemplate(self):
        """ Use a template if the `mainView' function doesn't exist. """
        return (not self.main_view)

    def isAdminPortalFeatured(self):
        """Don't display in the long list of additional modules if it's already featured
        in the main portion of the admin portal"""
        return self.module.handler in ['AdminCore', 'AdminMorph', 'AdminMaterials',
                                       'ListGenModule', 'ResourceModule', 'CommModule',
                                       'VolunteerManage', 'ClassFlagModule', 'ProgramPrintables',
                                       'AJAXSchedulingModule', 'NameTagModule', 'TeacherEventsModule']

    def isCompleted(self):
        return False

    def prepare(self, context):
        return context

    def getTemplate(self):
        if self.module.inline_template:
            return 'program/modules/%s/%s' % (self.__class__.__name__.lower(), self.module.inline_template)
        return None

    def teacherDesc(self):
        """
        A dict of string keys to descriptions (strings).

        Keys should be consistent with those of the teachers method.
        """
        return {}

    def teachers(self, QObject=False):
        """
        A dict of string keys to lists/QuerySets of teachers.

        String keys should be distinct across modules, unless the modules are
        mutually exclusive. Used for features like computing stats for the
        dashboard and selecting users for the comm panel.
        """
        return {}

    def studentDesc(self):
        """
        A dict of string keys to descriptions (strings).

        Keys should be consistent with those of the students method.
        """
        return {}

    def students(self, QObject=False):
        """
        A dict of string keys to lists/QuerySets of students.

        String keys should be distinct across modules, unless the modules are
        mutually exclusive. Used for features like computing stats for the
        dashboard and selecting users for the comm panel.
        """
        return {}

    def volunteerDesc(self):
        """
        A dict of string keys to descriptions (strings).

        Keys should be consistent with those of the volunteers method.
        """
        return {}

    def volunteers(self, QObject=False):
        """
        A dict of string keys to lists/QuerySets of volunteers.

        String keys should be distinct across modules, unless the modules are
        mutually exclusive. Used for features like computing stats for the
        dashboard and selecting users for the comm panel.
        """
        return {}

    def isStep(self):
        return True

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
        - "choosable" (as 0, namely that it displays as an option for admins to choose upon creating a new program)
        """

        props = cls.module_properties()

        def update_props(props):
            if not "handler" in props:
                props["handler"] = cls.__name__
            if not "admin_title" in props:
                props["admin_title"] = "%(link_title)s (%(handler)s)" % props
            if not "seq" in props:
                props["seq"] = 200
            if not "choosable" in props:
                props["choosable"] = 0
                raise AttributeError("Module `{}` doesn't have choosable property.".format(cls.__name__))

        if isinstance(props, dict):
            props = [ props ]

        for prop in props:
            update_props(prop)

        return props

    class Meta:
        app_label = 'modules'
        unique_together = ('program', 'module')


# will check and depending on the value of tl
# will use .isTeacher or .isStudent()
def not_logged_in(request):
    return (not request.user or not request.user.is_authenticated() or not request.user.id)

def usercheck_usetl(method):
    """
    Check that the user has the correct role based on tl.
    Will error if used on json or volunteer modules.
    """
    def _checkUser(moduleObj, request, tl, *args, **kwargs):
        error_map = {'learn': 'notastudent.html',
                     'teach': 'notateacher.html',
                     'manage': 'notanadmin.html',
                     'onsite': 'notonsite.html'
                     }
        errorpage = 'errors/program/' + error_map[tl]

        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if request.user.isAdmin(moduleObj.program) or \
           (tl == 'learn' and request.user.isStudent()) or \
           (tl == 'teach' and request.user.isTeacher()) or \
           (tl == 'onsite' and request.user.isOnsite()):
            return method(moduleObj, request, tl, *args, **kwargs)
        else:
            return render_to_response(errorpage, request, {})

    _checkUser.has_auth_check = True
    return _checkUser

def no_auth(method):
    method.has_auth_check = True
    return method

def needs_teacher(method):
    def _checkTeacher(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not request.user.isTeacher() and not request.user.isAdmin(moduleObj.program):
            return render_to_response('errors/program/notateacher.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkTeacher.call_tl = 'teach'
    _checkTeacher.method = method
    _checkTeacher.has_auth_check = True
    return _checkTeacher

def needs_admin(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if 'user_morph' in request.session:
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
    _checkAdmin.has_auth_check = True
    return _checkAdmin

def needs_onsite(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not request.user.isOnsite(moduleObj.program) and not request.user.isAdmin(moduleObj.program):
            user = request.user
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, {})
            user.switch_back(request)
        return method(moduleObj, request, *args, **kwargs)
    _checkAdmin.call_tl = 'onsite'
    _checkAdmin.method = method
    _checkAdmin.has_auth_check = True
    return _checkAdmin

def needs_onsite_no_switchback(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not request.user.isOnsite(moduleObj.program) and not request.user.isAdmin(moduleObj.program):
            user = request.user
            user.updateOnsite(request)
            ouser = user.get_old(request)
            if not user.other_user or (not ouser.isOnsite(moduleObj.program) and not ouser.isAdmin(moduleObj.program)):
                return render_to_response('errors/program/notonsite.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkAdmin.call_tl = 'onsite'
    _checkAdmin.method = method
    _checkAdmin.has_auth_check = True
    return _checkAdmin

def needs_student(method):
    def _checkStudent(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        if not request.user.isStudent() and not request.user.isAdmin(moduleObj.program):
            return render_to_response('errors/program/notastudent.html', request, {})
        return method(moduleObj, request, *args, **kwargs)
    _checkStudent.call_tl = 'learn'
    _checkStudent.method = method
    _checkStudent.has_auth_check = True
    return _checkStudent

def needs_account(method):
    def _checkAccount(moduleObj, request, *args, **kwargs):
        if not_logged_in(request):
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        return method(moduleObj, request, *args, **kwargs)
    _checkAccount.method = method
    _checkAccount.has_auth_check = True
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
            return render_to_response(errorpage, request, {
                    'program': moduleObj.program,
                    'yog': request.user.getYOG(moduleObj.program),
                })

        return method(moduleObj, request, tl, *args, **kwargs)

    return _checkGrade

def _checkDeadline_helper(method, extension, moduleObj, request, tl, *args, **kwargs):
    """
    Decide if a user can view a requested page; if not, offer a redirect.

    Given information about a request, return a pair of type (bool, None |
    response), which indicates whether the user can view the requested page,
    and an optional redirect if not.

    If the user is an administrator, annotate the request with information
    about what roles have permission to view the requested page.
    """
    if tl != 'learn' and tl != 'teach' and tl != 'volunteer':
        return (True, None)
    response = None
    canView = False
    perm_name = {'learn':'Student','teach':'Teacher','volunteer':'Volunteer'}[tl]+extension
    if not_logged_in(request):
        if not moduleObj.require_auth() and Permission.null_user_has_perm(permission_type=perm_name, program=request.program):
            canView = True
        else:
            response = HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
    else:
        user = request.user
        program = request.program
        canView = user.updateOnsite(request)
        if not canView:
            canView = Permission.user_has_perm(user,
                                               perm_name,
                                               program=program)
            #   For now, allow an exception if the user is of the wrong type
            #   This is because we are used to UserBits having a null user affecting everyone, regardless of user type.
            if not canView and Permission.valid_objects().filter(permission_type=perm_name, program=program, user__isnull=True).exists():
                canView = True

            #   Give administrators additional information
            if user.isAdministrator(program=program):
                request.show_perm_info = True
                if getattr(request, 'perm_names', None) is not None:
                    request.perm_names.append(perm_name)
                else:
                    request.perm_names = [perm_name]

                roles_with_perm = Permission.list_roles_with_perm(perm_name, program)
                if getattr(request, 'roles_with_perm', None) is not None:
                    request.roles_with_perm += roles_with_perm
                else:
                    request.roles_with_perm = roles_with_perm

    return (canView, response)

def list_extensions(tl, extensions, andor=''):
    nicetl={'teach':'Teacher','learn':'Student','volunteer':'Volunteer'}[tl]
    if len(extensions)==0:
        return 'no deadlines were'
    elif len(extensions)==1:
        return 'the deadline '+nicetl+extensions[0]+' was'
    elif len(extensions)==2:
        return 'the deadlines '+nicetl+extensions[0]+' '+andor+' '+nicetl+extensions[1]+' were'
    else:
        return 'the deadlines '+', '.join([nicetl+e for e in extensions[:-1]])+', '+andor+' '+nicetl+extensions[-1]+' were'

def render_deadline_for_tl(tl, request, context):
    errorpage = 'errors/program/deadline-%s.html' % tl
    return render_to_response(errorpage, request, context)

def meets_deadline(extension=''):
    """
    Decorate a function to check if a deadline is met.

    Return a decorator that returns a function calling the decorated function if
    the deadline is met, or a function that generates an error page if the
    deadline is not met.
    """
    return meets_any_deadline([extension])

def meets_any_deadline(extensions=[]):
    """
    Decorate a function to check if at least one deadline is met.

    Return a decorator that returns a function calling the decorated function
    if at least one of the deadlines is met, or a function that generates an
    error page if none of the deadlines are met.
    """
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            for ext in extensions:
                (canView, response) = _checkDeadline_helper(method, ext, moduleObj, request, tl, *args, **kwargs)
                if canView:
                    return method(moduleObj, request, tl, *args, **kwargs)
            if response:
                return response
            else:
                return render_deadline_for_tl(tl, request,
                        {'extension': list_extensions(tl,extensions,'and') , 'moduleObj': moduleObj})
        return _checkDeadline
    return meets_deadline

def meets_cap(view_method):
    """Only allow students who meet the program cap past this point."""
    @wraps(view_method, assigned=available_attrs(view_method))
    def _meets_cap(moduleObj, request, tl, one, two, module, extra, prog,
                   *args, **kwargs):
        if prog.user_can_join(request.user):
            return view_method(moduleObj, request, tl, one, two, module, extra,
                               prog, *args, **kwargs)
        else:
            return render_to_response('errors/program/program_full.html',
                                      request, {'moduleObj': moduleObj})
    return _meets_cap


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
            return render_deadline_for_tl(tl, request,
                    {'extension': error_message, 'moduleObj': moduleObj})
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
