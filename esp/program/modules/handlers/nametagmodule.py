from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models import ESPUser

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
            students = self.program.students_union()
            from esp.users.models import User
            from django.db.models import Q
            users = []
            students = [ ESPUser(student) for student in students ]
            students.sort()

            
            for student in students:
                users.append({'title': 'Student',
                              'name' : '%s %s' % (student.first_name, student.last_name),
                              'id'   : student.id})
                
        elif idtype == 'teacher':
            teachers = self.program.teachers()
            users = []
            teachers.sort()

            for teacher in teachers:
                users.append({'title': 'Teacher',
                              'name' : '%s %s' % (teacher.first_name, teacher.last_name),
                              'id'   : teacher.id})

        elif idtype == 'volunteers':
            users = []
            volunteers = request.POST['volunteers']
            for user in volunteers.split("\n"):
                arruser = user.split(",")
                if len(arruser) >= 2:
                    users.append({'title': arruser[1].strip(),
                                  'name' : arruser[0].strip(),
                                  'id'   : ''})
                
                
        elif idtype == 'blank':
            users = []
            for i in range(int(request.POST['number'])):
                users.append({'title': 'Student',
                              'name' : '',
                              'id'   : ''})
                
        numperpage = 6

        expanded = [[] for i in range(numperpage)]

        for i in range(len(users)):
            expanded[(i*numperpage)/len(users)].append(users[i])

        users = []

        for i in range(len(expanded[0])):
            for j in range(len(expanded)):
                if len(expanded[j]) <= i:
                    users.append({'title': 'Student',
                                  'name' : '',
                                  'id'   : ''})
                else:
                    users.append(expanded[j][i])

        context['users'] = users
            
        return render_to_response(self.baseDir()+'ids.html', request, (prog, tl), context)
        
