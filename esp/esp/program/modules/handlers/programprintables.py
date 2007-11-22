
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
from esp.money.models import LineItem, LineItemType

class ProgramPrintables(ProgramModuleObj):
    """ This is extremely useful for printing a wide array of documents for your program.
    Things from checklists to rosters to attendance sheets can be found here. """

    @needs_admin
    def paid_list_filter(self, request, tl, one, two, module, extra, prog):
        lineitemtypes = LineItemType.forAnchor(prog.anchor)
        context = { 'lineitemtypes': lineitemtypes }
        return render_to_response(self.baseDir()+'paid_list_filter.html', request, (prog, tl), context)

    @needs_admin
    def paid_list(self, request, tl, one, two, module, extra, prog):

        if request.GET.has_key('filter'):
            try:
                ids = [ int(x) for x in request.GET.getlist('filter') ]
                single_select = ( len(ids) == 1 )
            except ValueError:
                ids = None
                single_select = False

            if ids == None:
                lineitems = LineItem.objects.filter(type__anchor=prog.anchor).order_by('type_id','user_id').select_related()
            else:
                lineitems = LineItem.objects.filter(type__anchor=prog.anchor, type__id__in=ids).order_by('type_id','user_id').select_related()
        else:
            single_select = False
            lineitems = LineItem.objects.filter(type__anchor=prog.anchor).order_by('type_id','user_id').select_related()


        def sort_fn(a,b):
            if a.user.last_name.lower() > b.user.last_name.lower():
                return 1
            return -1

        lineitems_list = list(lineitems)
        lineitems_list.sort(sort_fn)

        context = { 'lineitems': lineitems_list,
                    'hide_paid': request.GET.has_key('hide_paid') and request.GET['hide_paid'] == 'True',
                    'prog': prog,
                    'single_select': single_select }

        return render_to_response(self.baseDir()+'paid_list.html', request, (prog, tl), context)

    
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

        order_by_time = False
        if request.GET.has_key('bytime'):
            order_by_time = True

        classes = [cls for cls in classes
                   if cls.isAccepted()   ]

        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids]

        if order_by_time:
            classes.sort()
        else:
            classes.sort(Class.catalog_sort)

        context = {'classes': classes, 'program': self.program}

        if extra is None or len(str(extra).strip()) == 0:
            extra = 'pdf'

        if order_by_time:
            return render_to_latex(self.baseDir()+'catalog_bytime.tex', context, extra)
        else:
            return render_to_latex(self.baseDir()+'catalog.tex', context, extra)

    @needs_admin
    def classesbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True):
        classes = Class.objects.filter(parent_program = self.program)

        classes = [cls for cls in classes
                   if cls.isAccepted()   ]
                   
        classes = filter(filt_exp, classes)                  

        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids]
            classes.sort(sort_exp)
            
        else:
            classes.sort(sort_exp)

        context = {'classes': classes, 'program': self.program}

        return render_to_response(self.baseDir()+'classes_list.html', request, (prog, tl), context)

    @needs_admin
    def classesbytime(self, request, tl, one, two, module, extra, prog):
        def cmp_time(one, other):
            if (one.meeting_times.count() > 0 and other.meeting_times.count() > 0):
                cmp0 = cmp(one.meeting_times.all()[0].start, other.meeting_times.all()[0].start)
            else:
                cmp0 = cmp(one.meeting_times.count(), other.meeting_times.count())

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)
        
        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_time)

    @needs_admin
    def classesbytitle(self, request, tl, one, two, module, extra, prog):
        def cmp_title(one, other):
            cmp0 = cmp(one.anchor.friendly_name, other.anchor.friendly_name)

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)
        
        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_title)

    @needs_admin
    def classesbyroom(self, request, tl, one, two, module, extra, prog):
        def cmp_room(one, other):
            room_one = one.initial_rooms()[0]
            room_other = other.initial_rooms()[0]
            
            cmp0 = cmp(room_one.name, room_other.name)

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)
        
        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_room)

    @needs_admin
    def teachersbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True):
        from esp.users.models import ContactInfo
        
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        teachers = [ ESPUser(user) for user in filterObj.getList(User).distinct() ]
        teachers.sort()

        scheditems = []

        for teacher in teachers:
            # get list of valid classes
            classes = [ cls for cls in teacher.getTaughtClasses()
                    if cls.parent_program == self.program
                    and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()

            # aseering 9-29-2007, 1:30am: There must be a better way to do this...
            ci = ContactInfo.objects.filter(user=teacher, phone_cell__isnull=False).exclude(phone_cell='').order_by('id')
            if ci.count() > 0:
                phone_cell = ci[0].phone_cell
            else:
                phone_cell = 'N/A'

            if len(classes) > 0:
                scheditems.append({'name': teacher.name(),
                               'user': teacher,
                               'phonenum': phone_cell,
                               'cls' : classes[0]})
        
        scheditems = filter(filt_exp, scheditems)
        scheditems.sort(sort_exp)

        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'teacherlist.html', request, (prog, tl), context)

    @needs_admin
    def teacherlist(self, request, tl, one, two, module, extra, prog):
        """ default list of teachers; function left in for compatibility """
        return self.teachersbyFOO(request, tl, one, two, module, extra, prog)

    @needs_admin
    def teachersbytime(self, request, tl, one, two, module, extra, prog):
        
        def cmpsort(one,other):
            if (one['cls'].meeting_times.count() > 0 and other['cls'].meeting_times.count() > 0):
                cmp0 = cmp(one['cls'].meeting_times.all()[0].start, other['cls'].meeting_times.all()[0].start)
            else:
                cmp0 = cmp(one['cls'].meeting_times.count(), other['cls'].meeting_times.count())
                
            if cmp0 != 0:
                return cmp0

            return cmp(one, other)

        return self.teachersbyFOO(request, tl, one, two, module, extra, prog, cmpsort)
            
    
    @needs_admin
    def teachersbyname(self, request, tl, one, two, module, extra, prog):
        
        def cmpsort(one,other):
            one_name = one['user'].last_name
            other_name = other['user'].last_name
            cmp0 = cmp(one_name, other_name)
                
            if cmp0 != 0:
                return cmp0

            return cmp(one['name'], other['name'])

        return self.teachersbyFOO(request, tl, one, two, module, extra, prog, cmpsort)

    @needs_admin
    def roomsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True):
        
        rooms = self.program.groupedClassrooms()
        rooms = filter(filt_exp, rooms)
        rooms.sort(sort_exp)

        context = {'rooms': rooms, 'program': self.program}

        return render_to_response(self.baseDir()+'roomlist.html', request, (prog, tl), context)
        
    @needs_admin
    def roomsbytime(self, request, tl, one, two, module, extra, prog):
        #   List of open classrooms, sorted by the first time they are available
        def filt(one):
            return one.available_any_time()
        
        def cmpsort(one, other):
            #   Find when available
            return cmp(one.available_times()[0], other.available_times()[0])

        return self.roomsbyFOO(request, tl, one, two, module, extra, prog, cmpsort, filt)
        

    @needs_admin
    def studentsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True):
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        students = filter(filt_exp, [ ESPUser(user) for user in filterObj.getList(User).distinct() ])
        students.sort()
        context['students'] = students
        
        return render_to_response(self.baseDir()+'studentlist.html', request, (prog, tl), context)
        
    @needs_admin
    def studentsbyname(self, request, tl, one, two, module, extra, prog):
        """ default function to get student list for program """
        return self.studentsbyFOO(request, tl, one, two, module, extra, prog)
        
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
        
        if key == 'receipt':
            #   Take the user's most recent registration profile.
            from django.template import Context, Template
            from django.template.loader import find_template_source
            from esp.settings import TEMPLATE_DIRS
            from esp.money.models import LineItem, LineItemType, RegisterLineItem
                
            prof = user.getLastProfile()
            
            for i in LineItemType.objects.filter(anchor=prof.program.anchor, optional=False):
                RegisterLineItem(user, i)
            
            context_dict = {'prog': prof.program, 'first_name': user.first_name, 'last_name': user.last_name, 'username': user.username, 'e_mail': prof.contact_user.e_mail, 'schedule': ProgramPrintables.getSchedule(prof.program, user)}
            
            context_dict['itemizedcosts'] = LineItem.purchased(prof.program.anchor, user, filter_already_paid=False)
            context_dict['itemizedcosttotal'] = LineItem.purchasedTotalCost(prof.program.anchor, user)
            context_dict['owe_money'] = ( context_dict['itemizedcosttotal'] != 0 )
            
            t = Template(open(TEMPLATE_DIRS + '/program/receipts/' + str(prof.program.id) + '_custom_receipt.txt').read())
            c = Context(context_dict)
            result_str = t.render(c)

            return result_str
            
        if key == 'schedule':
            return ProgramPrintables.getSchedule(self.program, user)
        if key == 'transcript':
            return ProgramPrintables.getTranscript(self.program, user, 'text')
        if key == 'transcript_html':
            return ProgramPrintables.getTranscript(self.program, user, 'html')
        if key == 'transcript_latex':
            return ProgramPrintables.getTranscript(self.program, user, 'latex')

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
                transactions = Transaction.objects.filter(fbo = user, anchor = self.program_anchor_cached())
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

        transactions = Transaction.objects.filter(fbo = user, anchor = self.program_anchor_cached())
        if transactions.count() == 0:
            transaction = Transaction()
        else:
            transaction = transactions[0]

        return render_to_response(self.baseDir()+'refund_receipt_form.html', request, (prog, tl), {'form': form,'student':user,
                                                                                                   'transaction': transaction})
    @staticmethod
    def get_student_classlist(program, student):
        
        # get list of valid classes
        classes = [ cls for cls in student.getEnrolledClasses()]

        # add taugtht classes
        classes += [ cls for cls in student.getTaughtClasses()  ]
            
        classes = [ cls for cls in classes
                    if cls.parent_program == program
                    and cls.isAccepted()                       ]
        # now we sort them by time/title
        classes.sort()
        
        return classes

    @staticmethod
    def getTranscript(program, student, format='text'):
        from django.template import Template, Context
        from django.template.loader import get_template

        template_keys = {   'text': 'program/modules/programprintables/transcript.txt',
                            'latex': 'program/modules/programprintables/transcript.tex',
                            'html': 'program/modules/programprintables/transcript.html',
                            'latex_desc': 'program/modules/programprintables/courses_inline.tex'
                        }
                        
        if format in template_keys:
            template_filename = template_keys[format]
        else:
            return ESPError('Attempted to get transcript with nonexistent format: %s' % format)

        t = get_template(template_filename)

        context = {'classlist': ProgramPrintables.get_student_classlist(program, student)}

        return t.render(Context(context))

    @staticmethod
    def getSchedule(program, student):
        
        
        schedule = """
Student schedule for %s:

 Time               | Class                                  | Room""" % student.name()

        
        classes = ProgramPrintables.get_student_classlist(program, student)
        
        for cls in classes:
            rooms = cls.prettyrooms()
            if len(rooms) == 0:
                rooms = 'N/A'
            else:
                rooms = ", ".join(rooms)
                
            schedule += """
%s|%s|%s""" % (",".join(cls.friendly_times()).ljust(20),
               cls.title().ljust(40),
               rooms)
               
        return schedule

    @needs_admin
    def onsiteregform(self, request, tl, one, two, module, extra, prog):

        # Hack together a pseudocontext:
        context = { 'onsiteregform': True,
                    'students': [{'classes': [{'friendly_times': [i.anchor.friendly_name],
                                               'classrooms': [''],
                                               'prettyrooms': ['______'],
                                               'title': '________________________________________',
                                               'getTeacherNames': [' ']} for i in prog.getTimeSlots()]}]
                    }
        return render_to_response(self.baseDir()+'studentschedule.html', request, (prog, tl), context)

    @needs_admin
    def studentschedules_finaid(self, request, tl, one, two, module, extra, prog):
        """ generate student schedules; now a unified function """
        return studentschedules(self, request, tl, one, two, module, extra, prog)
    
    def studentschedules(self, request, tl, one, two, module, extra, prog):
        """ generate student schedules """
        from esp.program.models import FinancialAidRequest
        from esp.money.models import LineItem, LineItemType, RegisterLineItem

        context = {'module': self     }

        if extra == 'onsite':
            students = [ESPUser(User.objects.get(id=request.GET['userid']))]
        else:
            filterObj, found = get_user_list(request, self.program.getLists(True))
    
            if not found:
                return filterObj

            students = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()
        
        scheditems = []

        for student in students:
            student.updateOnsite(request)
            # get list of valid classes
            classes = [ cls for cls in student.getEnrolledClasses()
                                if cls.parent_program == self.program
                                and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()
            
            #   add financial aid information
            for i in LineItemType.objects.filter(anchor=prog.anchor, optional=False):
                RegisterLineItem(student, i)
                
            student.itemizedcosts = LineItem.purchased(prog.anchor, student, filter_already_paid=False)
            student.itemizedcosttotal = LineItem.purchasedTotalCost(prog.anchor, student)
            student.has_paid = ( student.itemizedcosttotal == 0 )
        
            student.payment_info = True
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
        students = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct()]

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
        from esp.cal.models import Event
        
        classes = [ cls for cls in self.program.classes()
                    if cls.isAccepted()                      ]
        context = {}
        classes.sort()

        rooms = {}
        scheditems = []

        for cls in classes:
            for room in cls.initial_rooms():
                for event_group in Event.collapse(list(cls.meeting_times.all())):
                    update_dict = {'room': room.name,
                                   'cls': cls,
                                   'timeblock': event_group}
                    if rooms.has_key(room.name):
                        rooms[room.name].append(update_dict)
                    else:
                        rooms[room.name] = [update_dict]
            
        for room_name in rooms:
            rooms[room_name].sort(key=lambda x: x['timeblock'])
            for val in rooms[room_name]:
                scheditems.append(val)
                
        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'roomrosters.html', request, (prog, tl), context)            
        

    @needs_admin
    def satprepreceipt(self, request, tl, one, two, module, extra, prog):
        from esp.money.models import Transaction
        
        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        context = {'module': self     }
        students = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()

        receipts = []
        for student in students:
            transactions = Transaction.objects.filter(fbo = student, anchor = self.program_anchor_cached())
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
        students = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct()]

        students.sort()
                                    
        finished_verb = GetNode('V/Finished')
        finished_qsc  = self.program_anchor_cached().tree_create(['SATPrepLabel'])
        
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
        teachers = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct()]
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


        students= [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).distinct() ]
        students.sort()

        studentList = []
        for student in students:
            t = Transaction.objects.filter(fbo = student, anchor = self.program_anchor_cached())
            
            paid_symbol = ''
            if t.count() > 0:
                paid_symbol = '?'
                for tr in t:
                    if tr.executed is True:
                        paid_symbol = 'X'

            studentList.append({'user': student, 'paid': paid_symbol})

        context['students'] = students
        context['studentList'] = studentList
        return render_to_response(self.baseDir()+'studentchecklist.html', request, (prog, tl), context)

    @needs_admin
    def classchecklists(self, request, tl, one, two, module, extra, prog):
        """ Gives you a checklist for each classroom with the students that are supposed to be in that
            classroom.  The form has boxes for payment and forms.  This is useful for the first day 
            of a program. """
        context = {'module': self}

        students= [ ESPUser(user) for user in self.program.students()['confirmed']]
        students.sort()
    
        class_list = []

        for c in self.program.classes():
            c.update_cache_students()
            class_dict = {'cls': c}
            student_list = []
            
            for student in c.students():
                t = Transaction.objects.filter(fbo = student, anchor = self.program_anchor_cached())
                
                paid_symbol = ''
                if t.count() > 0:
                    paid_symbol = '?'
                    for tr in t:
                        if tr.executed is True:
                            paid_symbol = 'X'
    
                student_list.append({'user': student, 'paid': paid_symbol})
            
            class_dict['students'] = student_list
            class_list.append(class_dict)

        context['class_list'] = class_list
        
        return render_to_response(self.baseDir()+'classchecklists.html', request, (prog, tl), context)

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

    @needs_admin
    def certificate(self, request, tl, one, two, module, extra, prog):
        from esp.web.util.latex import render_to_latex
        
        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user

        if extra:
            file_type = extra.strip()
        else:
            file_type = 'pdf'

        context = {'user': user, 'prog': prog, 
                    'schedule': ProgramPrintables.getTranscript(prog, user, 'latex'),
                    'descriptions': ProgramPrintables.getTranscript(prog, user, 'latex_desc')}

        return render_to_latex(self.baseDir()+'completion_certificate.tex', context, file_type)
        
