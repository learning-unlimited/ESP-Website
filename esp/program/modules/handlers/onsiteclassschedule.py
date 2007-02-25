from django.http     import HttpResponseRedirect
from esp.users.views import search_for_user
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite



class OnsiteClassSchedule(ProgramModuleObj):


        
    @needs_onsite
    def schedule_students(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """

        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user
        
        self.user.switch_to_user(request,
                                 user,
                                 self.getCoreURL(tl),
                                 'OnSite Registration!',
                                 True)

        return HttpResponseRedirect('/learn/%s/studentreg' % self.program.getUrlBase())
