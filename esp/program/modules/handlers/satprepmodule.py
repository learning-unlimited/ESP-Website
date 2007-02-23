from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser
from django.db.models import Q



class SATPrepModule(ProgramModuleObj):

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'diag_sat_scores' or key == 'old_sat_scores':
            test_type = key.split('_')[0]
            
            if user.isStudent():
                foo = SATPrepRegInfo.getLastForProgram(user, self.program)
                scores = 'Your diagnostic SAT scores:\n'
                for test in ['Math','Verbal','Writing']:
                    curscore = foo.__dict__['%s_%s_score' % (test_type, test[0:4].lower())]
                    if curscore is None or curscore < 200 or curscore > 800:
                        scores += '%s: Not Available\n' % test
                    else:
                        scores += '%s: %s\n' % (test, curscore)
                return scores

        return ''
    
    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': self.getQForUser(Q(satprepreginfo__program = self.program)),
                    'satprep_mathdiag': self.getQForUser(Q(satprepreginfo__diag_math_score__isnull = False)),
                    'satprep_mathold' : self.getQForUser(Q(satprepreginfo__old_math_score__isnull = False)),
                    'satprep_writdiag': self.getQForUser(Q(satprepreginfo__diag_writ_score__isnull = False)),
                    'satprep_writold': self.getQForUser(Q(satprepreginfo__old_writ_score__isnull = False)),
                    'satprep_verbdiag': self.getQForUser(Q(satprepreginfo__diag_verb_score__isnull = False)),
                    'satprep_verbold': self.getQForUser(Q(satprepreginfo__old_verb_score__isnull = False))}
        
        studentswritold = ESPUser.objects.filter(Q(satprepreginfo__old_writ_score__isnull = False)).distinct()
        studentsmathold = ESPUser.objects.filter(Q(satprepreginfo__old_math_score__isnull = False)).distinct()
        studentsverbold = ESPUser.objects.filter(Q(satprepreginfo__old_verb_score__isnull = False)).distinct()
        
        studentswritdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_writ_score__isnull = False)).distinct()
        studentsmathdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_math_score__isnull = False)).distinct()
        studentsverbdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_verb_score__isnull = False)).distinct()

        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()

        return {'satprepinfo': students,
                'satprep_mathold': studentsmathold,
                'satprep_verbold': studentsverbold,
                'satprep_writold': studentswritold,
                'satprep_mathdiag': studentsmathdiag,
                'satprep_verbdiag': studentsverbdiag,
                'satprep_writdiag': studentswritdiag}
    

    def studentDesc(self):
        return {'satprepinfo': """Students who have filled out the SAT Prep information.""",
                'satprep_mathdiag': """Students who have an SAT math diagnostic score.""",
                'satprep_writdiag': """Students who have an SAT writing diagnostic score.""",
                'satprep_verbdiag': """Students who have an SAT verbal diagnostic score.""",
                'satprep_mathold': """Students who have an old SAT math score.""",
                'satprep_writold': """Students who have an old SAT writing score.""",
                'satprep_verbold': """Students who have an old SAT verbal score."""}
    
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

