from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser
from esp.program.models  import Class

class ProgramPrintables(ProgramModuleObj):

    @needs_admin
    def printoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self}

        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), context)



    @needs_admin
    def teacherschedules(self, request, tl, one, two, module, extra, prog):
        """ generate teacher schedules """

        context = {'module': self     }
        teachers = self.program.teachers()
        teachers.sort()

        scheditems = []

        for teacher in teachers:
            # get list of valid classes
            for cls in [ cls for cls in teacher.getTaughtClasses()
                         if cls.parent_program == self.program
                         and cls.isAccepted()                  ]:
            
                scheditems.append({'name': teacher.name(),
                                   'cls' : cls})

        context['scheditems'] = scheditems
        return render_to_response(self.baseDir()+'teacherschedule.html', request, (prog, tl), context)
        
    @needs_admin
    def studentschedules(self, request, tl, one, two, module, extra, prog):
        """ generate teacher schedules """

        context = {'module': self     }
        students = self.program.students()
        students.sort()

        scheditems = []

        for student in students:
            # get list of valid classes
            for cls in [ cls for cls in student.getEnrolledClasses()
                         if cls.parent_program == self.program
                         and cls.isAccepted()                  ]:
            
                scheditems.append({'name': student.name(),
                                   'cls' : cls})

        context['scheditems'] = scheditems
        return render_to_response(self.baseDir()+'studentschedule.html', request, (prog, tl), context)

    @needs_admin
    def roomrosters(self, request, tl, one, two, module, extra, prog):
        """ generate class room rosters"""
        classes = [ cls for cls in self.program.classes()
                    if cls.accepted()                      ]

        classes.sort()

        rooms = {}
        scheditems = []

        for cls in classes:
            roomassignments = cls.classroomassignments()
            for roomassignment in roomassignments:
                pass
        
            
        
        
    @needs_admin
    def classrosters(self, request, tl, one, two, module, extra, prog):
        """ generate teacher schedules """

        context = {'module': self     }
        teachers = self.program.teachers()
        teachers.sort()

        scheditems = []

        for teacher in teachers:
            for cls in teacher.getTaughtClasses().filter(parent_program = self.program):
                if cls.isAccepted():
                    scheditems.append({'teacher': teacher,
                                       'cls'    : cls})

        context['scheditems'] = scheditems
        return render_to_response(self.baseDir()+'classrosters.html', request, (prog, tl), context)
        

    @needs_admin
    def teacherlabels(self, request, tl, one, two, module, extra, prog):
        context = {'module': self}
        teachers = self.program.teachers()
        teachers.sort()
        context['teachers'] = teachers
        return render_to_response(self.baseDir()+'teacherlabels.html', request, (prog, tl), context)

    @needs_admin
    def studentchecklist(self, request, tl, one, two, module, extra, prog):
        context = {'module': self}
        students = self.program.students()
        students.sort()
        context['students'] = students
        return render_to_response(self.baseDir()+'studentchecklist.html', request, (prog, tl), context)


    @needs_admin
    def adminbinder(self, request, tl, one, two, module, extra, prog):
        if extra not in ['teacher','classid','timeblock']:
            return self.goToCore()
        context = {'module': self}

        scheditems = []

        
        if extra == 'teacher':
            teachers = self.program.teachers()
            teachers.sort()
            map(ESPUser, teachers)
            
            scheditems = []

            for teacher in teachers:
                classes = [ cls for cls in teacher.getTaughtClasses()
                            if cls.isAccepted() and
                               cls.parent_program == self.program     ]
                for cls in classes:
                    scheditems.append({'teacher': teacher,
                                       'class'  : cls})

            context['scheditems'] = scheditems
            return render_to_response(self.baseDir()+'adminteachers.html', request, (prog, tl), context)


        
        if extra == 'classid':
            classes = [cls for cls in self.program.classes()
                       if cls.isAccepted()                   ]

            classes.sort(Class.idcmp)

            for cls in classes:
                for teacher in cls.teachers():
                    teacher = ESPUser(teacher)
                    scheditems.append({'teacher': teacher,
                                      'class'  : cls})
            context['scheditems'] = scheditems                    
            return render_to_response(self.baseDir()+'adminclassid.html', request, (prog, tl), context)


        if extra == 'timeblock':
            classes = [cls for cls in self.program.classes()
                       if cls.isAccepted()                   ]

            classes.sort()
            
            for cls in classes:
                for teacher in cls.teachers():
                    teacher = ESPUser(teacher)
                    scheditems.append({'teacher': teacher,
                                      'cls'  : cls})

            context['scheditems'] = scheditems
            return render_to_response(self.baseDir()+'adminclasstime.html', request, (prog, tl), context)        

