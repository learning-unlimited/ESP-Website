from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.web.views.myesp import profile_editor
from esp.program.models import TeacherBio
from esp.users.models   import ESPUser
from django.db.models import Q

# reg profile module
class TeacherBioModule(ProgramModuleObj):
    """ Module for teacher to edit their biography for each program. """

    def teachers(self, QObject = False):
        if QObject:
            return {'teacher_biographies': self.getQForUser(Q(teacherbio__program = self.program))}
                    
        teachers = ESPUser.objects.filter(teacherbio__isnull = False).distinct()
        return {'teacher_biographies': teachers }

    def teacherDesc(self):
        return {'teacher_biographies': """Teachers who have completed the biography."""}

    def biography(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
        from esp.web.views import bio_edit
        result = bio_edit(request, tl, self.user.last_name, self.user.id, self.program.id, True)

        if result is not True:
            return result

        return self.goToCore(tl)

    def isCompleted(self):
        lastBio = TeacherBio.getLastForProgram(self.user, self.program)
        return lastBio.id is not None

