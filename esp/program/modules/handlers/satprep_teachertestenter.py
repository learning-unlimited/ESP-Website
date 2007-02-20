from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.web.views.myesp import search_for_user
from esp.program.manipulators import SATPrepDiagManipulator
from django import forms
from esp.program.models import SATPrepRegInfo


class SATPrepTeacherInput(ProgramModuleObj):

    
    @needs_teacher
    def satprepuserdiagnostic(self, request, tl, one, two, module, extra, prog):
        context = {}
        response, userfound = search_for_user(request, self.program.students_union())
        if not userfound:
            return response
        user = response
        
        manipulator = SATPrepDiagManipulator()
        new_data = {}
        if request.method == 'POST':
                new_data = request.POST.copy()

                errors = manipulator.get_validation_errors(new_data)

                if not errors:
                        manipulator.do_html2python(new_data)
                        new_reginfo = SATPrepRegInfo.getLastForProgram(user, prog)
                        new_reginfo.addOrUpdate(new_data, user, prog)

                        return self.goToCore(tl)
        else:
                satPrep = SATPrepRegInfo.getLastForProgram(user, prog)

                new_data = satPrep.updateForm(new_data)
                errors = {}

        form = forms.FormWrapper(manipulator, new_data, errors)
        return render_to_response(self.baseDir()+'satprep_diag.html', request, (prog, tl), {'form':form,
                                                                                            'user':user})


        

        




    def isStep(self):
        return False
    
