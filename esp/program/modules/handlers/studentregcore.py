from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.data        import render_to_response

class StudentRegCore(ProgramModuleObj):
  
    @needs_student
    @meets_deadline()
    def studentreg(self, request, tl, one, two, module, extra, prog):
    	    """ Display a student reg page """
	    context = {}
            modules = prog.getModules(self.user, 'learn')

	    context['completedAll'] = True
            for module in modules:
                if not module.isCompleted() and module.required:
                    context['completedAll'] = False

                context = module.prepare(context)

                    
	    context['modules'] = modules
	    context['one'] = one
	    context['two'] = two
            context['coremodule'] = self
            context['isConfirmed'] = self.program.isConfirmed(self.user)

	    return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False

