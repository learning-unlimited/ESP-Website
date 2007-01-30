from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.web.myesp import profile_editor
from esp.program.models import RegistrationProfile
from esp.users.models   import ESPUser
from django.db.models import Q

# reg profile module
class RegProfileModule(ProgramModuleObj):

    def students(self, QObject = False):
        if QObject:
            return {'profile': Q(registrationprofile__program = self.program) & \
                               Q(registrationprofile__student_info__isnull = False)}
        students = ESPUser.objects.filter(registrationprofile__program = self.program, registrationprofile__student_info__isnull = False).distinct()
        return {'profile': students }

    def profile(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
	from esp.web.myesp import profile_editor
        role = {'teach': 'teacher','learn': 'student'}[tl]

	response = profile_editor(request, prog, False, role)
	if response == True:
            return self.goToCore(tl)
	return response

    def isCompleted(self):
        regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
        return regProf.id is not None

