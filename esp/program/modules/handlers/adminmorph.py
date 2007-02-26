from django.http     import HttpResponseRedirect
from esp.users.views import search_for_user
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite
from esp.program.modules.handlers import ProgramPrintables
from esp.users.models import ESPUser

class AdminMorph(ProgramModuleObj):
    """ User morphing allows the program director to morph into a constituent of their program. """

    @needs_admin
    def admin_morph(self, request, tl, one, two, module, extra, prog):
        """ This function will allow someone to morph into a user for testing purposes. """
        
        Q_Everyone = self.program.students_union(True) | self.program.teachers_union(True)
        
        user, found = search_for_user(request, ESPuser.objects.filter(Q_Everyone))

        if not found:
            return user

        self.user.switch_to_user(request,
                                 user,
                                 self.getCoreURL(tl),
                                 'Managing %s' % self.program.niceName(),
                                 False)

        return HttpResponseRedirect('/')
