from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.users.views import search_for_user, get_user_list
from django import forms
from esp.program.models import SATPrepRegInfo



class SATPrepAdminSchedule(ProgramModuleObj):
    """ This allows SATPrep directors to schedule their programs using
        an algorithm. """
    def extensions(self):
        return [('satprepInfo', module_ext.SATPrepAdminModuleInfo)]

    @needs_admin
    def schedule_options(self, request, tl, one, two, module, extra, prog):
        """ This is a list of the two options required to schedule an
            SATPrep class. """
        
        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {})
    
