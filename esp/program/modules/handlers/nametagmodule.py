from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required


class NameTagModule(ProgramModuleObj):

    @needs_admin
    def selectidoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self}

        return render_to_response(self.baseDir()+'selectoptions.html', request, (prog, tl), context)



    @needs_admin
    def generatetags(self, request, tl, one, two, module, extra, prog):
        """ generate nametags """

        context = {'module': self,
                   'programname': request.POST['progname']                   
                   }

        idtype = request.POST['type']

        if idtype == 'students':
            students = self.program.students()
            users = []
            for student in students:
                users.append({'title': 'Student',
                              'name' : '%s %s' % (student.first_name, student.last_name),
                              'id'   : student.id})

            context['users'] = users

        return render_to_response(self.baseDir()+'ids.html', request, (prog, tl), context)
        
