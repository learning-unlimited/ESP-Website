
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
from esp.program.models import Program, ProgramModule
from esp.users.models import ESPUser
from esp.web.util import render_to_response
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth import LOGIN_URL, REDIRECT_FIELD_NAME
from urllib import quote
from esp.db.models import Q


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

    def docs(self):
        if self.__doc__ is not None and str(self.__doc__).strip() != '':
            return self.__doc__
        return self.module.link_title

    def __str__(self):
        return '"%s" for "%s"' % (self.module.admin_title, str(self.program))

    class Admin:
        pass

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
    
    def save(self):
        """ I'm doing this because DJango doesn't know what object inheritance is..."""
        if type(self) == ProgramModuleObj:
            return super(ProgramModuleObj, self).save()
        baseObj = ProgramModuleObj()
        baseObj.__dict__ = self.__dict__
        return baseObj.save()

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
            
        
        
    @staticmethod
    def findModule(request, tl, one, two, call_txt, extra, prog):
        modules = ProgramModule.objects.filter(main_call = call_txt,
                                               module_type = tl)

        module = None

        if modules.count() == 0:
            modules = ProgramModule.objects.filter(aux_calls__contains = call_txt,
                                                   module_type = tl)
            for module in modules:
                if call_txt in module.aux_calls.strip().split(','):
                    break
            if not module:
                raise Http404
        else:
            module = modules[0]


        if module:
            moduleobjs = ProgramModuleObj.objects.filter(module = module, program = prog)
            moduleobj = module.getPythonClass()()
            if len(moduleobjs) == 0:
                moduleobj.module = module
                moduleobj.program = prog
                moduleobj.seq = module.seq
                moduleobj.required = module.required
                moduleobj.save()
            else:
                moduleobj.__dict__.update(moduleobjs[0].__dict__)

        else:
            raise Http404

        moduleobj.request = request
        moduleobj.user    = ESPUser(request.user)
        moduleobj.fixExtensions()

        if hasattr(moduleobj, call_txt):
            return getattr(moduleobj, call_txt)(request, tl, one, two, call_txt, extra, prog)

        raise Http404


    @staticmethod
    def getFromProgModule(prog, mod):
        import esp.program.modules.models
        """ Return an appropriate module object for a Module and a Program.
           Note that all the data is forcibly taken from the ProgramModuleObj table """
        ModuleObj   = mod.getPythonClass()()
        BaseModuleList = ProgramModuleObj.objects.filter(program = prog, module = mod)
        if len(BaseModuleList) < 1:
            ModuleObj.program = prog
            ModuleObj.module  = mod
            ModuleObj.seq     = mod.seq
            ModuleObj.required = mod.required
            ModuleObj.save()

        elif len(BaseModuleList) > 1:
            assert False, 'Too many module objects!'
        else:
            ModuleObj.__dict__.update(BaseModuleList[0].__dict__)
        
        ModuleObj.fixExtensions()

        return ModuleObj



    def getClassFromId(self, clsid, tl='teach'):
        """ This function can be called from a view to get a class object from an id. The id can be given
            with request or extra, but it will try to get it in any way. """

        from esp.program.models import Class

        classes = []
        try:
            clsid = int(clsid)
        except:
            return (False, True)
        
        classes = Class.objects.filter(id = clsid)
            
        if len(classes) == 1:
            if not self.user.canEdit(classes[0]):
                raise ESPError(False), 'You do not have permission to edit %s.' %\
                      classes[0].title()
            else:
                Found = True
                return (classes[0], True)
        return (False, False)
            

    def baseDir(self):
        return 'program/modules/'+self.__class__.__name__.lower()+'/'

    def fixExtensions(self):
        
        for x in self.extensions():
            k, obj = x
            newobj = obj.objects.filter(module = self)
            if len(newobj) == 0 or len(newobj) > 1:
                self.__dict__[k] = obj()
                self.__dict__[k].module = self
                self.__dict__[k].save()
            else:
                self.__dict__[k] = newobj[0]


    def deadline_met(self, extension=''):
    
        from esp.users.models import UserBit
        from esp.datatree.models import GetNode


        if not self.user or not self.program:
            raise ESPError(False), "There is no user or program object!"


            
        if self.module.module_type != 'learn' and self.module.module_type != 'teach':
            return True

        canView = False

        if self.user.__dict__.has_key('onsite_local'):
            canView = self.user.__dict__['onsite_local']

        if not canView:
            canView = UserBit.UserHasPerms(self.user,
                                           self.program.anchor,
                                           GetNode('V/Deadline/Registration/'+{'learn':'Student',
                                                                               'teach':'Teacher'}[self.module.module_type]+extension))


        return canView

    # important functions for hooks...

    def get_full_path(self):
        str_array = self.program.anchor.tree_encode()
        url = '/'+self.module.module_type \
              +'/'+'/'.join(str_array[2:])+'/'+self.module.main_call
        return url

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
            return '<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
                   (self.get_full_path(), self.module.link_title, self.module.link_title)

        return '<a href="%s" title="%s" onmouseover="updateDocs(\'<p>%s</p>\');" class="vModuleLink" >%s</a>' % \
               (self.get_full_path(), self.module.link_title, self.docs().replace("'", "\\'").replace('\n','<br />\\n').replace('\r', ''), self.module.link_title)


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
        return 'program/modules/'+self.__class__.__name__.lower()+'/'+ \
               self.module.main_call+'.html'

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

    def getNavBars(self):
        return []

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
            return render_to_response(errorpage, {})
        
        if tl == 'teach' and not moduleObj.user.isTeacher():
            return render_to_response(errorpage, {})
        
        if tl == 'manage' and not moduleObj.user.isAdmin(moduleObj.program):
            return render_to_response(errorpage, {})

        return method(moduleObj, request, tl, *args, **kwargs)

    return _checkUser


def needs_teacher(method):
    def _checkTeacher(moduleObj, request, *args, **kwargs):
        
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        if not moduleObj.user.isTeacher():
            return render_to_response('errors/program/notateacher.html', request, (moduleObj.program, 'teach'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkTeacher

def needs_admin(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isAdmin(moduleObj.program):
            return render_to_response('errors/program/notanadmin.html', request, (moduleObj.program, 'manage'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkAdmin

def needs_onsite(method):
    def _checkAdmin(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isOnsite(moduleObj.program) and not moduleObj.user.isAdmin(moduleObj.program):
            return render_to_response('errors/program/notonsite.html', request, (moduleObj.program, 'onsite'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkAdmin


def needs_student(method):
    def _checkStudent(moduleObj, request, *args, **kwargs):
        if not moduleObj.user or not moduleObj.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))

        if not moduleObj.user.isStudent():
            return render_to_response('errors/program/notastudent.html', request, (moduleObj.program, 'learn'), {})
        return method(moduleObj, request, *args, **kwargs)

    return _checkStudent        


def meets_grade(method):
    def _checkGrade(moduleObj, request, tl, *args, **kwargs):
        errorpage = 'errors/program/wronggrade.html'
        from esp.datatree.models import GetNode
        from esp.users.models import UserBit

        verb_override = GetNode('V/Flags/Registration/GradeOverride')

        # if there's grade override we can just skip everything
        if UserBit.UserHasPerms(user = moduleObj.user,
                                  qsc  = moduleObj.program.anchor,
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
def meets_deadline(extension=''):
    def meets_deadline(method):
        def _checkDeadline(moduleObj, request, tl, *args, **kwargs):
            errorpage = 'errors/program/deadline-%s.html' % tl
            from esp.users.models import UserBit
            from esp.datatree.models import GetNode
            if tl != 'learn' and tl != 'teach':
                return True

            canView = moduleObj.user.updateOnsite(request)
            if not canView:
                canView = UserBit.UserHasPerms(moduleObj.user,
                                               moduleObj.program.anchor,
                                               GetNode('V/Deadline/Registration/'+{'learn':'Student',
                                                                               'teach':'Teacher'}[tl]+extension))

            if canView:
                return method(moduleObj, request, tl, *args, **kwargs)
            else:
                return render_to_response(errorpage, request, (moduleObj.program, tl), {})

        return _checkDeadline

    return meets_deadline


