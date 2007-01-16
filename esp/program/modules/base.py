from django.db import models
from esp.program.models import Program, ProgramModule
import esp.program.modules.models
from esp.users.models import ESPUser

class ProgramModuleObj(models.Model):
    program  = models.ForeignKey(Program)
    module   = models.ForeignKey(ProgramModule)
    seq      = models.IntegerField()
    required = models.BooleanField()

    def __str__(self):
        return self.module.admin_title

    class Admin:
        pass

    def all_views(self):
        if self.module and self.module.aux_calls:
            return self.module.aux_calls.strip(',').split(',')

        return []

    def save(self):
        if type(self) == ProgramModuleObj:
            return super(ProgramModuleObj, self).save()
        baseObj = ProgramModuleObj()
        baseObj.__dict__ = self.__dict__
        return baseObj.save()

    @staticmethod
    def find_module(request, tl, one, two, call_txt, extra, prog):
        module_list = prog.getModules()
        # first look for a mainview
        for moduleObj in module_list:
            moduleObj.setUser(ESPUser(request.user))
            
            if moduleObj.module and call_txt == moduleObj.module.main_call \
               and hasattr(moduleObj, moduleObj.module.main_call):
                return moduleObj.mainView(request, tl, one, two, call_txt, extra, prog)

        # now look for auxillary views
        for moduleObj in module_list:
            for aux_call in moduleObj.all_views():
                if call_txt == aux_call and hasattr(moduleObj, aux_call):
                    return getattr(moduleObj, aux_call)(request, tl, one, two, call_txt, extra, prog)
            
        return False

    @staticmethod
    def getFromProgModule(prog, mod):
        """ Return an appropriate module object for a Module and a Program.
           Note that all the data is forcibly taken from the ProgramModuleObj table """
        modulesList = esp.program.modules.models.__dict__

        if not mod.handler or not modulesList.has_key(mod.handler):
            assert False, 'Module name not in global scope.'

        ModuleClass = modulesList[mod.handler]
        ModuleObj   = ModuleClass()
        BaseModuleList = ProgramModuleObj.objects.filter(program = prog, module = mod)
        if len(BaseModuleList) < 1:
            ModuleObj.program = prog
            ModuleObj.module  = mod
            ModuleObj.seq     = mod.seq
            ModuleObj.required = mod.required
        else:
            ModuleObj.__dict__.update(BaseModuleList[0].__dict__)
            ModuleObj.fixExtensions()

        return ModuleObj

    def fixExtensions(self):
        
        for x in self.extensions():
            k, obj = x
            newobj = obj.objects.filter(module = self)
            if len(newobj) == 0 or len(newobj) > 1:
                self.__dict__[k] = None
            else:
                self.__dict__[k] = newobj[0]
        

    # important functions for hooks...

    def setUser(self, user):
        self.curUser = user


    def makeLink(makeLink):
        str_array = self.program.anchor.tree_encode()
        # ugly dictionary which should be removed at some point
        url = '/'+{'student_reg':'learn',
                   'teacher_reg':'teach',
                   'learn': 'learn',
                   'teach': 'teach',
                   'admin':'admin',
                   'onsite':'onsite'}[self.module.module_type] \
              +'/'+'/'.join(str_array[2:])+'/'+self.module.main_call
        
        return '<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
               (url, self.module.link_title, self.module.link_title)


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
        return 'program/modules/'+self.module.main_call+'.html'


    def standardStep(self):
        return True

    def extensions(self):
        return []
