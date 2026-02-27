from django.utils.encoding import python_2_unicode_compatible
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
from urllib.parse import quote
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

def _login_redirect(request):
    return HttpResponseRedirect(
        '%s?%s=%s' % (settings.LOGIN_URL, REDIRECT_FIELD_NAME,
                      quote(request.get_full_path())))

class CoreModule(object):
    """
    All core modules should derive from this.
    """
    pass

@python_2_unicode_compatible
class ProgramModuleObj(models.Model):
    program  = models.ForeignKey(Program, on_delete=models.CASCADE)
    module   = models.ForeignKey(ProgramModule, on_delete=models.CASCADE)
    seq      = models.IntegerField()
    required = models.BooleanField(default=False)
    required_label = models.CharField(max_length=80, blank=True, null=False, default="")

    def docs(self):
        if hasattr(self, 'doc') and self.doc is not None and str(self.doc).strip() != '':
            return self.doc
        return self.module.link_title

    def __str__(self):
        return '"%s" for "%s"' % (self.module.admin_title, str(self.program))

    def _get_views_by_call_tag(self, tags):
        """ We define decorators below (aux_call, main_call, etc.) which allow
            methods within the ProgramModuleObj subclass to be tagged with
            metadata.  At the moment, this metadata is a string stored in the
            'call_tag' attribute.  This function searches the methods of the
            current program module to find those that match the list supplied
            in the 'tags' argument. """
        result = []

        #   Filter out attributes that we don't want to look at: attributes of
        #   ProgramModuleObj, including Django stuff
        key_set = set(dir(self)) - set(dir(ProgramModuleObj)) - set(self.__class__._meta.get_fields())
        for key in key_set:
            #   Fetch the attribute, now that we're confident it's safe to look at.
            item = getattr(self, key)
            #   This is a hack to test whether the item is a bound method,
            #   maybe there is a better way.
            if isinstance(item, type(self._get_views_by_call_tag)) and hasattr(item, 'call_tag'):
                if item.call_tag in tags:
                    result.append(key)

        return result

    @property
    def main_view(self):
        """The name of the module's main view."""
        if not hasattr(self, '_main_view'):
            main_views = self._get_views_by_call_tag(['Main Call'])
            if len(main_views) > 1:
                raise ESPError("Module %s has multiple main calls." % self.module.handler)
            elif main_views:
                self._main_view = main_views[0]
            else:
                self._main_view = None
        return self._main_view

    def main_view_fn(self, request, tl, one, two, call_txt, extra, prog):
        return getattr(self, self.main_view)(request, tl, one, two, call_txt, extra, prog)

    @property
    def views(self):
        if not hasattr(self, '_views'):
            self._views = self._get_views_by_call_tag(['Main Call', 'Aux Call'])
        return self._views

    def get_msg_vars(self, user, key):
        return None

    def getCoreURL(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(get_current_request().user, tl)
        for module in modules:
            if isinstance(module, CoreModule):
                return module.get_full_path()

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
    def findRequiredModules(self):
        """Includes only required modules"""
        prog = self.program
        module_type = self.module.module_type
        moduleobjs = [mod for mod in prog.getModules() if mod.module.module_type == module_type and mod.isRequired() == True]
        moduleobjs.sort(key=lambda mod: mod.seq)
        return moduleobjs
    #   Program.getModules cache takes care of our dependencies
    findRequiredModules.depend_on_cache(Program.getModules_cached, lambda **kwargs: {})

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
                    return _login_redirect(request)
                for m in moduleobj.findRequiredModules():
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
            raise ESPError(False)("There is no user or program object!")

        if self.module.module_type != 'learn' and self.module.module_type != 'teach':
            return True

        canView = user.isOnsite(self.program) or user.isAdministrator(self.program)

        if not canView:
            deadline = {'learn':'Student', 'teach':'Teacher'}[self.module.module_type]+extension
            canView = Permission.user_has_perm(user, deadline, program=self.program)

        return canView

    # important functions for hooks...
    @cache_function
    def get_full_path(self):
        return '/%s/%s/%s' % (
            self.module.module_type, self.program.url, self.main_view)
    get_full_path.depend_on_row('modules.ProgramModuleObj', 'self')
    get_full_path.depend_on_model('program.Program')

    def makeLink(self):
        if not self.module.module_type == 'manage':
            link = '<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
                (self.get_full_path(), self.module.link_title, self.module.link_title)
        else:
            link = '<a href="%s" title="%s" onmouseover="updateDocs(\'<p>%s</p>\');" class="vModuleLink" >%s</a>' % \
               (self.get_full_path(), self.module.link_title, self.docs().replace("'", "\\'").replace('\n', '<br />\\n').replace('\r', ''), self.module.link_title)

        return mark_safe(link)

    def makeSelfCheckinLink(self):
        return self.makeLink()

    def get_setup_title(self):
        if hasattr(self, 'setup_title') and self.setup_title is not None and str(self.setup_title).strip() != '':
            return self.setup_title
        return self.module.link_title

    def get_setup_path(self):
        if hasattr(self, 'setup_path') and self.setup_path is not None and str(self.setup_path).strip() != '':
            path = self.setup_path
        else:
            path = self.main_view
        return '/manage/' + self.program.url + '/' + path

    def makeSetupLink(self):
        title = self.get_setup_title()
        link = self.get_setup_path()
        return mark_safe('<a href="%s" title="%s">%s</a>' % (link, title, title))

    def makeButtonLink(self):
        if not self.module.module_type == 'manage':
            link = """<div class="module_button">\
                                <a href="%s"><button type="button" class="module_link_large">
                                    <div class="module_link_main">%s</div>
                                </button></a>
                            </div>""" % (self.get_full_path(), self.module.link_title)
        else:
            link = '<a href="%s" onmouseover="updateDocs(\'<p>%s</p>\');"></a><button type="button" class="module_link_large btn btn-default btn-lg"> <div class="module_link_main">%s%s</div></button></a>' % \
               (self.get_full_path(), self.docs().replace("'", "\\'").replace('\n', '<br />\\n').replace('\r', ''), self.module.link_title, self.module.handler)

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
                                       'AJAXSchedulingModule', 'NameTagModule', 'TeacherEventsManageModule',
                                       'SurveyManagement']
    def isOnSiteFeatured(self):
        """Don't display in the long list of additional modules if it's already featured
        in the main portion of the admin portal"""
        return self.module.handler in ['OnSiteCheckinModule', 'TeacherCheckinModule', 'OnSiteCheckoutModule',
                                       'OnsiteClassSchedule', 'OnSiteClassList', 'OnSiteRegister',
                                       'OnSiteAttendance', 'OnsitePaidItemsModule']
    def isCompleted(self):
        return False

    def isRequired(self):
        return self.required

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

    def inModulesList(self):
        return self.isStep()

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
    return (not request.user or not request.user.is_authenticated or not request.user.id)

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
            return _login_redirect(request)

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

def render_deadline_for_tl(tl, request, context):
    errorpage = 'errors/program/deadline-%s.html' % tl
    return render_to_response(errorpage, request, context)

def user_passes_test(test_func, error_message=None, error_template=None,
                     error_context_var='extension', extra_context_func=None,
                     require_login=True, call_tl=None):
    """A method decorator for ProgramModuleObj view methods.

    Requests pass through only if test_func(moduleObj, request) returns True.
    On failure, an error page is rendered.

    This is the primary building block for access-control decorators in this
    module. Simple decorators such as needs_teacher, needs_student, and
    meets_cap are implemented using this function.

    Parameters
    ----------
    test_func : callable(moduleObj, request) -> bool
        Determines whether the request should pass through.
    error_message : str, optional
        Value of the ``error_context_var`` template variable on failure.
        When using the default render_deadline_for_tl() fallback, format
        this similarly to the output of list_extensions().
    error_template : str, optional
        Path to a specific template to render on failure. If None, falls
        back to render_deadline_for_tl(), which renders the per-tl deadline
        error template (errors/program/deadline-<tl>.html).
    error_context_var : str
        Template variable name for error_message. Defaults to 'extension'.
    extra_context_func : callable(moduleObj, request) -> dict, optional
        Called on failure to supply additional variables to the error template.
    require_login : bool
        If True (default), redirect unauthenticated users to the login page.
        Set to False when a surrounding decorator already handles login.
    call_tl : str, optional
        If provided, the wrapper function will have this as its call_tl
        attribute (e.g., 'learn', 'teach', 'manage', 'onsite').
    """
    def decorator(view_method):
        @wraps(view_method, assigned=available_attrs(view_method))
        def _check(moduleObj, request, tl, *args, **kwargs):
            if require_login and not_logged_in(request):
                return _login_redirect(request)
            if test_func(moduleObj, request):
                return view_method(moduleObj, request, tl, *args, **kwargs)
            context = {'moduleObj': moduleObj}
            if error_message is not None:
                context[error_context_var] = error_message
            if extra_context_func is not None:
                context.update(extra_context_func(moduleObj, request))
            if error_template is not None:
                return render_to_response(error_template, request, context)
            return render_deadline_for_tl(tl, request, context)
        _check.has_auth_check = True
        _check.method = view_method
        if call_tl is not None:
            _check.call_tl = call_tl
        return _check
    return decorator


def _meets_grade_test(moduleObj, request):
    """Return True if the user meets the program's grade range requirement."""
    if Permission.user_has_perm(request.user, 'GradeOverride', moduleObj.program):
        return True
    cur_grade = request.user.getGrade(moduleObj.program)
    return not (cur_grade != 0 and (
        cur_grade < moduleObj.program.grade_min or
        cur_grade > moduleObj.program.grade_max
    ))


def _meets_grade_extra_context(moduleObj, request):
    """Extra template context for the wronggrade error page."""
    return {
        'program': moduleObj.program,
        'yog': request.user.getYOG(moduleObj.program),
    }


meets_grade = user_passes_test(
    _meets_grade_test,
    error_template='errors/program/wronggrade.html',
    extra_context_func=_meets_grade_extra_context,
    require_login=False,
)

needs_student = user_passes_test(
    lambda moduleObj, request: (
        request.user.isStudent() or request.user.isAdmin(moduleObj.program)
    ),
    error_template='errors/program/notastudent.html',
    call_tl='learn',
)

def needs_student_in_grade(method):
    """Require that the user is a logged-in student within the program grade range.

    Combines needs_student (login + student/admin check) with meets_grade
    (grade range check) so that each failure renders the appropriate error
    page (notastudent.html or wronggrade.html respectively).
    """
    decorated = needs_student(meets_grade(method))
    # Override .method to point to the original unwrapped function, consistent
    # with the convention used by the other auth decorators.
    decorated.method = method
    return decorated

needs_teacher = user_passes_test(
    lambda moduleObj, request: (
        request.user.isTeacher() or request.user.isAdmin(moduleObj.program)
    ),
    error_template='errors/program/notateacher.html',
    call_tl='teach',
)

def needs_admin(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if 'user_morph' in request.session:
            morpheduser=ESPUser.objects.get(id=request.session['user_morph']['olduser_id'])
        else:
            morpheduser=None

        if not_logged_in(request):
            return _login_redirect(request)

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
            return _login_redirect(request)

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
            return _login_redirect(request)

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

needs_account = user_passes_test(
    lambda moduleObj, request: True,
    require_login=True,
)

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
    perm_name = {'learn':'Student','teach':'Teacher','volunteer':'Volunteer'}[tl]+extension
    if not_logged_in(request):
        if not moduleObj.require_auth() and Permission.null_user_has_perm(permission_type=perm_name, program=request.program):
            return (True, None)
        else:
            return (False, _login_redirect(request))
    else:
        user = request.user
        program = request.program
        canView = user.updateOnsite(request)
        request.mod_required = moduleObj.isRequired()
        request.tl = tl
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
                request.one = program.program_type
                request.two = program.program_instance
                if getattr(request, 'perm_names', None) is not None:
                    request.perm_names.append(perm_name)
                else:
                    request.perm_names = [perm_name]

                roles_with_perm = Permission.list_roles_with_perm(perm_name, program)
                if getattr(request, 'roles_with_perm', None) is not None:
                    request.roles_with_perm += roles_with_perm
                else:
                    request.roles_with_perm = roles_with_perm

        return (canView, None)

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
                        {'extension': list_extensions(tl, extensions, 'and') , 'moduleObj': moduleObj})
        return _checkDeadline
    return meets_deadline

meets_cap = user_passes_test(
    lambda moduleObj, request: moduleObj.program.user_can_join(request.user),
    error_template='errors/program/program_full.html',
    require_login=False,
)


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
