from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser
from django.db.models import Q



class SATPrepModule(ProgramModuleObj):

    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': Q(satprepreginfo__program = self.program)}
        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()
        return {'satprepinfo': students }

    def isCompleted(self):
        
	satPrep = SATPrepRegInfo.getLastForProgram(self.user, self.program)
	return satPrep.id is not None


    @needs_student
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
	manipulator = SATPrepInfoManipulator()
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
			manipulator.do_html2python(new_data)
			new_reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
			new_reginfo.addOrUpdate(new_data, request.user, prog)

                        return self.goToCore(tl)
	else:
		satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
		
		new_data = satPrep.updateForm(new_data)
		errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})

