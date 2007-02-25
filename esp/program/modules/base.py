""" This module houses the base ProgramModuleObj from which all module handlers are derived.
    There are many useful and magical functions provided in here, most of which can be called
    from within the program handler.
"""

from django.db import models
from esp.program.models import Program, ProgramModule
from esp.users.models import ESPUser
from esp.web.util import render_to_response
from django.http import HttpResponseRedirect
from django.contrib.auth import LOGIN_URL, REDIRECT_FIELD_NAME
from urllib import quote
from django.db.models import Q


class ProgramModuleObj(models.Model):
    program  = models.ForeignKey(Program)
    module   = models.ForeignKey(ProgramModule)
    seq      = models.IntegerField()
    required = models.BooleanField()

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
            if type(module) == esp.program.modules.models.StudentRegCore or \
               type(module) == esp.program.modules.models.TeacherRegCore or \
               type(module) == esp.program.modules.models.AdminCore or \
               type(module) == esp.program.modules.models.OnsiteCore:
                return getattr(module, module.module.main_call)
        assert False, 'No core module to return to!'

    def getCoreURL(self, tl):
        import esp.program.modules.models
        modules = self.program.getModules(self.user, tl)
        for module in modules:
             if type(module) == esp.program.modules.models.StudentRegCore or \
               type(module) == esp.program.modules.models.TeacherRegCore or \
               type(module) == esp.program.modules.models.AdminCore or \
               type(module) == esp.program.modules.models.OnsiteCore:
                 return '/'+tl+'/'+self.program.getUrlBase()+'/'+module.module.main_call


    def goToCore(self, tl):
        return HttpResponseRedirect(self.getCoreURL(tl))

    def getQForUser(self, QRestriction):
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
    def findModule(request, tl, one, two, call_txt, extra, prog):
        module_list = prog.getModules(ESPUser(request.user), tl)
        # first look for a mainview
        for moduleObj in module_list:
            moduleObj.request = request
    
        for moduleObj in module_list:
            if moduleObj.module and call_txt == moduleObj.module.main_call \
               and hasattr(moduleObj, moduleObj.module.main_call):
                return getattr(moduleObj, moduleObj.module.main_call)(request, tl, one, two, call_txt, extra, prog)

        # now look for auxillary views
        for moduleObj in module_list:
            for aux_call in moduleObj.all_views():
                if call_txt == aux_call and hasattr(moduleObj, aux_call):
                    return getattr(moduleObj, aux_call)(request, tl, one, two, call_txt, extra, prog)
            
        return False

    @staticmethod
    def getFromProgModule(prog, mod):
        import esp.program.modules.models
        """ Return an appropriate module object for a Module and a Program.
           Note that all the data is forcibly taken from the ProgramModuleObj table """
        modulesList = esp.program.modules.models.__dict__

        if not mod.handler or not modulesList.has_key(mod.handler):
            return None
            assert False, 'Module name "%s" not in global scope.' % mod.handler

        ModuleClass = modulesList[mod.handler]
        ModuleObj   = ModuleClass()
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

        canView = self.user.onsite_local
        
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


    def setUser(self, user):
        self.user = user
        self.curUser = user


    def makeLink(self):
        return '<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
               (self.get_full_path(), self.module.link_title, self.module.link_title)


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
        is_onsite = moduleObj.user.updateOnsite(request)

        if is_onsite:
            url = moduleObj.user.switch_back(request)
            return HttpResponseRedirect(request.path)
        
        if not moduleObj.user.isOnsite(moduleObj.program) and \
           not moduleObj.user.isAdmin(moduleObj.program):
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

