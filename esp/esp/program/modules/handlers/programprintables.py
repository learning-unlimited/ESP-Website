
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import GetNode
from esp.money.models    import Transaction
from esp.program.models  import Class
from esp.users.views     import get_user_list, search_for_user
from esp.web.util.latex  import render_to_latex

class ProgramPrintables(ProgramModuleObj):
    """ This is extremely useful for printing a wide array of documents for your program.
    Things from checklists to rosters to attendance sheets can be found here. """
    
    @needs_admin
    def printoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self}

        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), context)

    @needs_admin
    def catalog(self, request, tl, one, two, module, extra, prog):
        " this sets the order of classes for the catalog. "

        if request.GET.has_key('ids') and request.GET.has_key('op') and \
           request.GET.has_key('clsid'):
            try:
                clsid = int(request.GET['clsid'])
                cls   = Class.objects.get(parent_program = self.program,
                                          id             = clsid)
            except:
                raise ESPError(), 'Could not get the class object.'

            classes = Class.objects.filter(parent_program = self.program)
            classes = [cls for cls in classes
                       if cls.isAccepted() ]

            cls_dict = {}
            for cur_cls in classes:
                cls_dict[str(cur_cls.id)] = cur_cls
            

            clsids = request.GET['ids'].split(',')
            found  = False
            
            if request.GET['op'] == 'up':
                for i in range(1,len(clsids)):
                    if not found and str(clsids[i]) == request.GET['clsid']:
                        tmp         = str(clsids[i-1])
                        clsids[i-1] = str(clsids[i])
                        clsids[i]   = tmp
                        found       = True
                        
            elif request.GET['op'] == 'down':
                for i in range(len(clsids)-1):
                    if not found and str(clsids[i]) == request.GET['clsid']:
                        tmp         = str(clsids[i])
                        clsids[i]   = str(clsids[i+1])
                        clsids[i+1] = tmp
                        found       = True
            else:
                raise ESPError(), 'Received invalid operation for class list.'

            
            classes = []

            for clsid in clsids:
                classes.append(cls_dict[clsid])

            clsids = ','.join(clsids)
            return render_to_response(self.baseDir()+'catalog_order.html',
                                      request,
                                      (self.program, tl),
                                      {'clsids': clsids, 'classes': classes})

        
        classes = Class.objects.filter(parent_program = self.program)

        classes = [cls for cls in classes
                   if cls.isAccepted()    ]

        classes.sort(Class.catalog_sort)

        clsids = ','.join([str(cls.id) for cls in classes])

        return render_to_response(self.baseDir()+'catalog_order.html',
                                  request,
                                  (self.program, tl),
                                  {'clsids': clsids, 'classes': classes})
        

    @needs_admin
    def coursecatalog(self, request, tl, one, two, module, extra, prog):
        " This renders the course catalog in LaTeX. "

        classes = Class.objects.filter(parent_program = self.program)


        classes = [cls for cls in classes
                   if cls.isAccepted()   ]

        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids]
            
        else:
            classes.sort(Class.catalog_sort)
        context = {'classes': classes, 'program': self.program}

        if extra is None or len(str(extra).strip()) == 0:
            extra = 'pdf'

        return render_to_latex(self.baseDir()+'catalog.tex', context, extra)
        


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
            return ProgramPrintables.getSchedule(self.program, user)

        return ''

    @needs_admin
    def refund_receipt(self, request, tl, one, two, module, extra, prog):
        from esp.money.models import Transaction
        from esp.web.util.latex import render_to_latex
        from esp.program.modules.forms.printables_refund import RefundInfoForm
        
        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user

        initial = {'userid': user.id }

        if request.GET.has_key('payer_post'):
            form = RefundInfoForm(request.GET, initial=initial)
            if form.is_valid():
                transactions = Transaction.objects.filter(fbo = user, anchor = self.program.anchor)
                if transactions.count() == 0:
                    transaction = Transaction()
                else:
                    transaction = transactions[0]

                context = {'user': user, 'transaction': transaction}
                context['program'] = prog

                context['payer_name'] = form.clean_data['payer_name']
                context['payer_address'] = form.clean_data['payer_address']                

                context['amount'] = '%.02f' % (transaction.amount)

                if extra:
                    file_type = extra.strip()
                else:
                    file_type = 'pdf'

                return render_to_latex(self.baseDir()+'refund_receipt.tex', context, file_type)
        else:
            form = RefundInfoForm(initial = initial)

        transactions = Transaction.objects.filter(fbo = user, anchor = self.program.anchor)
        if transactions.count() == 0:
            transaction = Transaction()
        else:
            transaction = transactions[0]

        return render_to_response(self.baseDir()+'refund_receipt_form.html', request, (prog, tl), {'form': form,'student':user,
                                                                                                   'transaction': transaction})

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

            student.classes = classes
            
        context['students'] = students
        return render_to_response(self.baseDir()+'studentschedule.html', request, (prog, tl), context)

    @needs_admin
    def flatstudentschedules(self, request, tl, one, two, module, extra, prog):
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
        return render_to_response(self.baseDir()+'flatstudentschedule.html', request, (prog, tl), context)


    @needs_admin
    def roomschedules(self, request, tl, one, two, module, extra, prog):
        """ generate class room rosters"""
        classes = [ cls for cls in self.program.classes()
                    if cls.isAccepted()                      ]
        context = {}
        classes.sort()

        rooms = {}
        scheditems = ['']

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
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        students = [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()
                                    
        finished_verb = GetNode('V/Finished')
        finished_qsc  = self.program.anchor.tree_create(['SATPrepLabel'])
        
        #if request.GET.has_key('print'):
            
        #    if request.GET['print'] == 'all':
        #        students = self.program.students_union()
        #    elif request.GET['print'] == 'remaining':
        #        printed_students = UserBit.bits_get_users(verb = finished_verb,
        #qsc  = finished_qsc)
        #        printed_students_ids = [user.id for user in printed_students ]
        #        if len(printed_students_ids) == 0:
        #            students = self.program.students_union()
        #        else:
        #            students = self.program.students_union().exclude(id__in = printed_students_ids)
        #    else:
        #        students = ESPUser.objects.filter(id = request.GET['print'])

        #    for student in students:
        #        ub, created = UserBit.objects.get_or_create(user      = student,
        #                                                    verb      = finished_verb,
        #                                                    qsc       = finished_qsc,
        #                                                    recursive = False)

        #        if created:
        #            ub.save()
                    
        #    students = [ESPUser(student) for student in students]
        #    students.sort()

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
    #return render_to_response(self.baseDir()+'SATPrepLabels_options.html', request, (prog, tl), {})
            
        
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
        if extra == 'attendance':
            tpl = 'classattendance.html'
        else:
            tpl = 'classrosters.html'
        return render_to_response(self.baseDir()+tpl, request, (prog, tl), context)
        

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


        students= [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct() ]
        students.sort()

        studentList = []
        for student in students:
            t = Transaction.objects.filter(fbo = student, anchor = self.program.anchor)
            if t.count() == 0:
                studentList.append({'user': student,
                                    'paid': False})
            else:
                studentList.append({'user': student,
                                    'paid': t[0].executed})


        context['students'] = students
        context['studentList'] = studentList
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


