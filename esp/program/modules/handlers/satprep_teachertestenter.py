from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode

class SATPrepTeacherInput(ProgramModuleObj):

    
    @needs_teacher
    def satprepdiag(self, request, tl, one, two, module, extra, prog):
        context = {}
        




    def isStep(self):
        return False
    
