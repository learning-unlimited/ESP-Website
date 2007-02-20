from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepTeacherInfoManipulator
from django import forms
from esp.program.models import Program
from esp.users.models   import ESPUser, User
from django.db.models import Q
from django.db        import models




class SATPrepTeacherModule(ProgramModuleObj):

    def teachers(self,QObject = False):
        if QObject:
            return {'teachers_satprepinfo': self.getQForUser(Q(satprepteachermoduleinfo__program = self.program))}
                    
        teachers = ESPUser.objects.filter(satprepteachermoduleinfo__program = self.program).distinct()
        return {'teachers_satprepinfo': teachers }

    def teacherDesc(self):
        return {'teachers_satprepinfo': """Teachers who have entered SATPrep-specific information."""}

    def isCompleted(self):
        return module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                       program = self.program).count() > 0


    @needs_teacher
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
        manipulator = SATPrepTeacherInfoManipulator(module_ext.SATPrepTeacherModuleInfo.subjects())
        
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
                    manipulator.do_html2python(new_data)
                    moduleinfos = module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                                                     program = self.program)
                    if len(moduleinfos) == 0:
                        new_reginfo = module_ext.SATPrepTeacherModuleInfo()
                        new_reginfo.user = self.user
                        new_reginfo.program = self.program
                    else:
                        new_reginfo = moduleinfos[0]

                    for k in new_data.keys():
                        new_reginfo.__dict__[k] = new_data[k]

                    new_reginfo.save()
                
                    return self.goToCore(tl)
	else:
                moduleinfos = module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                                                 program = self.program)
                if len(moduleinfos) == 0:
                    new_data = {}
                else:
                    new_data = moduleinfos[0].__dict__
		
		errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response(self.baseDir()+'satprep_info.html', request, (prog, tl), {'form':form})

