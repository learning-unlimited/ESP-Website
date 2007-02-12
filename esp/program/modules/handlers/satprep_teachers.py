from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from esp.program.models import Program
from esp.users.models   import ESPUser, User
from django.db.models import Q
from django.db        import models


class SATPrepTeacherModuleInfo(models.Model):
    """ Module that links a user with a program and has SATPrep teacher info"""
    SAT_SUBJECTS = (
        ('M', 'Math'),
        ('V', 'Verbal'),
        ('W', 'Writing')
        )
    sat_math = models.PositiveIntegerField(blank=True, null=True)
    sat_writ = models.PositiveIntegerField(blank=True, null=True)
    sat_verb = models.PositiveIntegerField(blank=True, null=True)

    subject  = models.CharField(maxlength=32, choices = SAT_SUBJECTS)

    user     = models.ForeignKey(User,blank=True, null=True)
    program  = models.ForeignKey(Program,blank=True, null=True)
   
    def __str__(self):
        return 'SATPrep Information for teacher %s in %s' % \
                 (str(self.user), str(self.program))

    class Admin:
        pass



class SATPrepTeacherModule(ProgramModuleObj):

    def teachers(self,QObject = False):
        if QObject:
            return {'satprepinfo_teachers': Q(id=-1)}
                    
        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()
        return {'satprepinfo': students }

    def studentDesc(self):
        return {'satprepinfo': """Students who have filled out the SAT Prep information."""}

    def isCompleted(self):
        
	satPrep = SATPrepRegInfo.getLastForProgram(self.user, self.program)
	return satPrep.id is not None


    @needs_teacher
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
        manipulator = SATPrepTeacherInfoManipulator()
        
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
	#		manipulator.do_html2python(new_data)
#			new_reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
		#	new_reginfo.addOrUpdate(new_data, request.user, prog)

                        return self.goToCore(tl)
	else:
		moduleinfos = SATPrepTeacherModuleInfo.objects.filer(user = self.user,
                                                                     program = self.program)
                if len(moduleinfos) == 0:
                    new_data = {}
                else:
                    new_data = moduleinfos[0].__dict__
		
		errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response(self.baseDir()+'satprep_info.html', request, (prog, tl), {'form':form})

