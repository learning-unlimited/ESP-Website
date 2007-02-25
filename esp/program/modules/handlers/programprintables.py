from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import GetNode
from esp.program.models  import Class
from esp.users.views     import get_user_list

class ProgramPrintables(ProgramModuleObj):

    @needs_admin
    def printoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self}

        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), context)


    @needs_admin
    def satprepStudentCheckboxes(self, request, tl, one, two, module, extra, prog):
        students = [ESPUser(student) for student in self.program.students_union() ]
        students.sort()
        return render_to_response(self.baseDir()+'satprep_students.html', request, (prog, tl), {'students': students})

    @needs_admin
    def teacherschedules(self, request, tl, one, two, module, extra, prog):
        """ generate teacher schedules """

        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj


        context = {'module': self     }
        teachers = [ ESPUser(user) for user in filterObj.getList(User).distinct()]
        teachers.sort()


        scheditems = []

        for teacher in teachers:
            # get list of valid classes
            classes = [ cls for cls in teacher.getTaughtClasses()
                    if cls.parent_program == self.program
                    and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()            
            for cls in classes:
            
                scheditems.append({'name': teacher.name(),
                                   'cls' : cls})

        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'teacherschedule.html', request, (prog, tl), context)
        
    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'schedule':
            return ProgramPrintables.getStudentSchedule(self.program, user)

        return ''

    @staticmethod
    def getSchedule(program, student):
        
        schedule = """
Student schedule for %s:

 Time               | Class                   | Room""" % student.name()

        
        # get list of valid classes
        classes = [ cls for cls in student.getEnrolledClasses()]

        # add taugtht classes
        classes += [ cls for cls in student.getTaughtClasses()  ]
            
        classes = [ cls for cls in classes
                    if cls.parent_program == program
                    and cls.isAccepted()                       ]
        # now we sort them by time/title
        classes.sort()
        
        for cls in classes:
            rooms = cls.prettyrooms()
            if len(rooms) == 0:
                rooms = 'N/A'
            else:
                rooms = ", ".join(rooms)
                
            schedule += """
%s|%s|%s""" % (",".join(cls.friendly_times()).ljust(20),
               cls.title().ljust(25),
               rooms)
               
        return schedule

    @needs_admin
    def studentschedules(self, request, tl, one, two, module, extra, prog):
        """ generate student schedules """

        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        students = [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()
        
        scheditems = []

        for student in students:
            # get list of valid classes
            classes = [ cls for cls in student.getEnrolledClasses()
                    if cls.parent_program == self.program
                    and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()
            
            for cls in classes:
                scheditems.append({'name': student.name(),
                                   'cls' : cls})

        context['scheditems'] = scheditems
        return render_to_response(self.baseDir()+'studentschedule.html', request, (prog, tl), context)

    @needs_admin
    def roomschedules(self, request, tl, one, two, module, extra, prog):
        """ generate class room rosters"""
        classes = [ cls for cls in self.program.classes()
                    if cls.isAccepted()                      ]
        context = {}
        classes.sort()

        rooms = {}
        scheditems = []

        for cls in classes:
            roomassignments = cls.classroomassignments()
            for roomassignment in roomassignments:
                if rooms.has_key(roomassignment.room.id):
                    rooms[roomassignment.room.id].append({'room':
                                                          roomassignment.room.name,
                                                          'cls': cls,
                                                          'timeblock':
                                                          roomassignment.timeslot.friendly_name})
                else:
                    rooms[roomassignment.room.id] = [{'room':
                                                      roomassignment.room.name,
                                                      'cls': cls,
                                                      'timeblock': roomassignment.timeslot.friendly_name}]
        for scheditem in rooms.values():
            for dictobj in scheditem:
                scheditems.append(dictobj)
                
        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'roomrosters.html', request, (prog, tl), context)            
        

    @needs_admin
    def satprepreceipt(self, request, tl, one, two, module, extra, prog):
        from esp.money.models import Transaction
        
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        students = [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()

        receipts = []
        for student in students:
            transactions = Transaction.objects.filter(fbo = student, anchor = self.program.anchor)
            if transactions.count() == 0:
                transaction = Transaction()
            else:
                transaction = transactions[0]

            receipts.append({'user': student, 'transaction': transaction})

        context['receipts'] = receipts
        
        return render_to_response(self.baseDir()+'studentreceipts.html', request, (prog, tl), context)
    
    @needs_admin
    def satpreplabels(self, request, tl, one, two, module, extra, prog):
        finished_verb = GetNode('V/Finished')
        finished_qsc  = self.program.anchor.tree_create(['SATPrepLabel'])
        
        if request.GET.has_key('print'):
            
            if request.GET['print'] == 'all':
                students = self.program.students_union()
            elif request.GET['print'] == 'remaining':
                printed_students = UserBit.bits_get_users(verb = finished_verb,
                                                          qsc  = finished_qsc)
                printed_students_ids = [user.id for user in printed_students ]
                if len(printed_students_ids) == 0:
                    students = self.program.students_union()
                else:
                    students = self.program.students_union().exclude(id__in = printed_students_ids)
            else:
                students = ESPUser.objects.filter(id = request.GET['print'])

            for student in students:
                ub, created = UserBit.objects.get_or_create(user      = student,
                                                            verb      = finished_verb,
                                                            qsc       = finished_qsc,
                                                            recursive = False)

                if created:
                    ub.save()
                    
            students = [ESPUser(student) for student in students]
            students.sort()

            numperpage = 10
            
            expanded = [[] for i in range(numperpage)]

            users = students
            
            for i in range(len(users)):
                expanded[(i*numperpage)/len(users)].append(users[i])

            users = []
                
            for i in range(len(expanded[0])):
                for j in range(len(expanded)):
                    if len(expanded[j]) <= i:
                        users.append(None)
                    else:
                        users.append(expanded[j][i])
            students = users
            return render_to_response(self.baseDir()+'SATPrepLabels_print.html', request, (prog, tl), {'students': students})
        else:
            return render_to_response(self.baseDir()+'SATPrepLabels_options.html', request, (prog, tl), {})
            
        
    @needs_admin
    def classrosters(self, request, tl, one, two, module, extra, prog):
        """ generate class rosters """


        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj


        context = {'module': self     }
        teachers = [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]
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
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        students= [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]
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

