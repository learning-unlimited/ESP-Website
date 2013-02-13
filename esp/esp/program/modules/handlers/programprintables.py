
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, needs_onsite_no_switchback, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import *
from esp.program.models  import ClassSubject, ClassSection, SplashInfo, FinancialAidRequest
from esp.users.views     import search_for_user
from esp.users.controllers.usersearch import UserSearchController
from esp.web.util.latex  import render_to_latex
from esp.accounting_docs.models import Document, MultipleDocumentError
from esp.accounting_core.models import LineItem, LineItemType, Transaction
from esp.tagdict.models import Tag
from esp.cal.models import Event
from esp.middleware import ESPError
from django.conf import settings
from django.template.loader import select_template
from django.utils.encoding import smart_str

from decimal import Decimal
import simplejson as json

class ProgramPrintables(ProgramModuleObj):
    """ This is extremely useful for printing a wide array of documents for your program.
    Things from checklists to rosters to attendance sheets can be found here. """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Program Printables",
            "module_type": "manage",
            "seq": 5
            }

    @aux_call
    @needs_admin
    def paid_list_filter(self, request, tl, one, two, module, extra, prog):
        lineitemtypes = LineItemType.objects.forProgram(prog)
        context = { 'lineitemtypes': lineitemtypes }
        return render_to_response(self.baseDir()+'paid_list_filter.html', request, (prog, tl), context)

    @aux_call
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
                lineitems = LineItem.objects.forProgram(prog).order_by('li_type','user').select_related()
            else:
                lineitems = LineItem.objects.forProgram(prog).filter(li_type__id__in=ids).order_by('li_type','user').select_related()
        else:
            single_select = False
            lineitems = LineItem.objects.forProgram(prog).order_by('li_type','user').select_related()
        
        for lineitem in lineitems:
            lineitem.has_financial_aid = ESPUser(lineitem.user).hasFinancialAid(prog.anchor)

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

    @main_call
    @needs_admin
    def printoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self, 'li_types': prog.getLineItemTypes(required=False)}

        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def catalog(self, request, tl, one, two, module, extra, prog):
        " this sets the order of classes for the catalog. "
        
        cmp_fn = { "": ClassSubject.class_sort_noop,
                   "category": ClassSubject.class_sort_by_category,
                   "id": ClassSubject.class_sort_by_id,
                   "teachers": ClassSubject.class_sort_by_teachers,
                   "title": ClassSubject.class_sort_by_title,
                   "timeblock": ClassSubject.class_sort_by_timeblock }

        sort_list = []
        sort_name_list = []
        grade_min = prog.grade_min
        grade_max = prog.grade_max
        grade_options = range(grade_min, grade_max + 1)
        category_options = prog.class_categories.all().values_list('category', flat=True)
        categories = category_options

        if request.GET.has_key('first_sort'):
            sort_list.append( cmp_fn[request.GET['first_sort']] )
            sort_name_list.append( request.GET['first_sort'] )
        else:
            sort_list.append( cmp_fn["category"] )

        if request.GET.has_key('second_sort'):
            sort_list.append( cmp_fn[request.GET['second_sort']] )
            sort_name_list.append( request.GET['second_sort'] )
        else:
            sort_list.append( cmp_fn["timeblock"] )

        if request.GET.has_key('third_sort'):
            sort_list.append( cmp_fn[request.GET['third_sort']] )
            sort_name_list.append( request.GET['third_sort'] )
        else:
            sort_list.append( cmp_fn["title"] )

        if 'categories' in request.GET:
            categories = request.GET.getlist('categories')
        if 'grade_min' in request.GET:
            grade_min = int(request.GET['grade_min'])
        if 'grade_max' in request.GET:
            grade_max = int(request.GET['grade_max'])

        classes = ClassSubject.objects.filter(parent_program = self.program, status__gt=0)
        classes = classes.filter(grade_min__lte=grade_max)
        classes = classes.filter(grade_max__gte=grade_min)
        classes = classes.filter(category__category__in=categories)
        classes = [cls for cls in classes
                   if cls.isAccepted() ]

        if request.GET.has_key('ids') and request.GET.has_key('op') and \
           request.GET.has_key('clsid'):
            try:
                clsid = int(request.GET['clsid'])
                cls   = ClassSubject.objects.get(parent_program = self.program,
                                          id             = clsid)
            except:
                raise ESPError(), 'Could not get the class object.'

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
                                      {'clsids': clsids, 'classes': classes, 'sorting_options': cmp_fn.keys(), 'sort_name_list': ",".join(sort_name_list), 'sort_name_list_orig': sort_name_list, 'category_options': category_options, 'grade_options': grade_options, 'grade_min_orig': grade_min, 'grade_max_orig': grade_max, 'categories_orig': categories })

        if request.GET.has_key("only_nonfull"):
            classes = [x for x in classes if not x.isFull()]

        sort_list_reversed = sort_list
        sort_list_reversed.reverse()
        for sort_fn in sort_list_reversed:
            classes.sort(sort_fn)

        clsids = ','.join([str(cls.id) for cls in classes])

        return render_to_response(self.baseDir()+'catalog_order.html',
                                  request,
                                  (self.program, tl),
                                  {'clsids': clsids, 'classes': classes, 'sorting_options': cmp_fn.keys(), 'sort_name_list': ",".join(sort_name_list), 'sort_name_list_orig': sort_name_list, 'category_options': category_options, 'grade_options': grade_options, 'grade_min_orig': grade_min, 'grade_max_orig': grade_max, 'categories_orig': categories  })
        

    @aux_call
    @needs_admin
    def coursecatalog(self, request, tl, one, two, module, extra, prog):
        " This renders the course catalog in LaTeX. "
        from django.conf import settings
        classes = ClassSubject.objects.filter(parent_program = self.program)

        if request.GET.has_key('mingrade'):
            mingrade=int(request.GET['mingrade'])
            classes = classes.filter(grade_max__gte=mingrade)

        if request.GET.has_key('maxgrade'):
            maxgrade=int(request.GET['maxgrade'])
            classes = classes.filter(grade_min__lte=maxgrade)

        if request.GET.has_key('open'):
            classes = [cls for cls in classes if not cls.isFull()]

        if request.GET.has_key('sort_name_list'):
            sort_name_list = request.GET['sort_name_list'].split(',')
            first_sort = sort_name_list[0] or 'category'
        else:
            first_sort = "category"

        #   Filter out classes that are not scheduled
        classes = [cls for cls in classes
                   if cls.isAccepted() and cls.sections.all().filter(meeting_times__isnull=False).exists() ]

        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids if cls_dict.has_key(clsid)]

        context = {'classes': classes, 'program': self.program}

        group_name = Tag.getTag('full_group_name')
        if not group_name:
            group_name = '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        context['group_name'] = group_name

        #   Hack for timeblock sorting
        if first_sort == 'timeblock':
            sections = []
            for cls in classes: 
                sections += list(x for x in cls.sections.all().filter(status__gt=0, meeting_times__isnull=False).distinct() if not (request.GET.has_key('open') and x.isFull()))
            sections.sort(key=lambda x: x.start_time())
            context['sections'] = sections

        if extra is None or len(str(extra).strip()) == 0:
            extra = 'pdf'

        return render_to_latex(self.baseDir()+'catalog_%s.tex' % first_sort, context, extra)

    @needs_admin
    def classesbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True):
        classes = ClassSubject.objects.filter(parent_program = self.program)

        classes = [cls for cls in classes
                   if cls.isAccepted()   ]
                   
        classes = filter(filt_exp, classes)                  

        if request.GET.has_key('grade_min'):
            classes = filter(lambda x: x.grade_max > int(request.GET['grade_min']), classes)

        if request.GET.has_key('grade_max'):
            classes = filter(lambda x: x.grade_min < int(request.GET['grade_max']), classes)

        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids]

        classes.sort(sort_exp)

        context = {'classes': classes, 'program': self.program}

        return render_to_response(self.baseDir()+'classes_list.html', request, (prog, tl), context)

    @needs_admin
    def sectionsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file='sections_list.html'):
        sections = self.program.sections()

        if extra == 'csv':
            template_file = 'sections_list.csv'

        if 'cancelled' in request.GET or (extra and 'cancelled' in extra):
            sections = filter(lambda z: (z.isCancelled() and z.meeting_times.count() > 0), sections)
        else:
            sections = filter(lambda z: (z.isAccepted() and z.meeting_times.count() > 0), sections)
        sections = filter(filt_exp, sections)                  

        if request.GET.has_key('grade_min'):
            sections = filter(lambda x: (x.parent_class.grade_max > int(request.GET['grade_min'])), sections)

        if request.GET.has_key('grade_max'):
            sections = filter(lambda x: (x.parent_class.grade_min < int(request.GET['grade_max'])), sections)

        if request.GET.has_key('secids'):
            clsids = request.GET['secids'].split(',')
            cls_dict = {}
            for cls in sections:
                cls_dict[str(cls.id)] = cls
            sections = [cls_dict[clsid] for clsid in clsids]

        sections.sort(sort_exp)

        context = {'sections': sections, 'program': self.program}

        return render_to_response(self.baseDir()+template_file, request, (prog, tl), context)

    @aux_call
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
        
        return self.sectionsbyFOO(request, tl, one, two, module, extra, prog, cmp_time)

    @aux_call
    @needs_admin
    def classesbytitle(self, request, tl, one, two, module, extra, prog):
        def cmp_title(one, other):
            cmp0 = cmp(one.anchor.friendly_name.upper().lstrip().strip('"\',.<![($'), other.anchor.friendly_name.upper().lstrip().strip('"\',.<![($'))

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)
        
        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_title)

    @aux_call
    @needs_admin
    def classesbyroom(self, request, tl, one, two, module, extra, prog):
        def cmp_room(one, other):
            qs_one = one.initial_rooms()
            qs_other = other.initial_rooms()
            cmp0 = 0
            
            if qs_one.count() > 0 and qs_other.count() > 0:
                room_one = qs_one[0]
                room_other = qs_other[0]
                cmp0 = cmp(room_one.name, room_other.name)

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)
        
        return self.sectionsbyFOO(request, tl, one, two, module, extra, prog, cmp_room)

    @aux_call
    @needs_admin
    def classesbyid(self, request, tl, one, two, module, extra, prog):
        def cmp_id(one, other):
            return cmp(one.id, other.id)
        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_id)

    @aux_call
    @needs_admin
    def classprereqs(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(parent_program = self.program)

        classes = [cls for cls in classes
                   if cls.isAccepted()   ]
        
        sort_exp = lambda x,y: ((x.title() != y.title()) and cmp(x.title().upper().lstrip().strip('"\',.<![($'), y.title().upper().lstrip().strip('"\',.<![($'))) or cmp(x.id, y.id)
        
        if request.GET.has_key('clsids'):
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids]
            classes.sort(sort_exp)
        else:
            classes.sort(sort_exp)
        
        for cls in classes:
            cls.implications = []
            for implication in cls.classimplication_set.filter(parent__isnull=True):
                imp_info = {}
                imp_info['operation'] = { 'AND':'All', 'OR':'Any', 'XOR':'Exactly one' }[implication.operation]
                imp_info['prereqs'] = ClassSubject.objects.filter(id__in = implication.member_id_ints)
                        #cls.prereqs += '<li>' + str(prereq_list[0].id) + ": " + prereq_list[0].title() + '<br />'
                        #cls.prereqs += '(' + prereq_list[0].friendly_times().join(', ') + ' in ' + prereq_list[0].prettyrooms().join(', ') + '</li>'
                cls.implications.append(imp_info)
        
        context = { 'classes': classes, 'program': self.program }
        return render_to_response(self.baseDir()+'classprereqs.html', request, (prog, tl), context)

    @needs_admin
    def teachersbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file = 'teacherlist.html', extra_func = lambda x: {}):
        from esp.users.models import ContactInfo

        if extra == 'csv':
            template_file = 'teacherlist.csv'
        
        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self     }
        teachers = list(filterObj.getList(ESPUser).distinct())
        for t in teachers:
            extra_dict = extra_func(t)
            for key in extra_dict:
                setattr(t, key, extra_dict[key])
        teachers.sort()

        if extra == 'secondday':
            from django.db.models import Min

            allclasses = prog.sections().filter(status=10, parent_class__status=10, meeting_times__isnull=False)
            first_timeblock_dict = allclasses.aggregate(Min('meeting_times__start'))


        scheditems = []
        resource_types = prog.getResourceTypes().values_list('name', flat=True)

        for teacher in teachers:
            # get list of valid classes
            classes = [ cls for cls in teacher.getTaughtSections(self.program)
                    if cls.isAccepted() and cls.meeting_times.count() > 0 ]
            # now we sort them by time/title
            classes.sort()

            if extra == 'secondday':
                new_classes = []
                first_timeblock = first_timeblock_dict['meeting_times__start__min']

                for cls in classes:
                    starttime = cls.meeting_times.all().order_by('start')[0]
                    if (starttime.start.month, starttime.start.day) != \
                       (first_timeblock.month, first_timeblock.day):
                        new_classes.append(cls)

                classes = new_classes

            # aseering 9-29-2007, 1:30am: There must be a better way to do this...
            ci = ContactInfo.objects.filter(user=teacher, phone_cell__isnull=False).exclude(phone_cell='').order_by('id')
            if ci.count() > 0:
                phone_day = ci[0].phone_day
                phone_cell = ci[0].phone_cell
            else:
                phone_day = 'N/A'
                phone_cell = 'N/A'

            if len(classes) > 0:
                scheditems.append({'name': teacher.name(),
                               'user': teacher,
                               'phone_day': phone_day,
                               'phone_cell': phone_cell,
                               'cls' : classes[0],
                               'res_values': [classes[0].resourcerequest_set.filter(res_type__name=x).values_list('desired_value', flat=True) for x in resource_types]})
        
        scheditems = filter(filt_exp, scheditems)
        scheditems.sort(sort_exp)

        context['res_types'] = resource_types
        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+template_file, request, (prog, tl), context)

    @aux_call
    @needs_admin
    def teacherlist(self, request, tl, one, two, module, extra, prog):
        """ default list of teachers; function left in for compatibility """
        return self.teachersbyFOO(request, tl, one, two, module, extra, prog)

    @aux_call
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
            

    @aux_call
    @needs_admin
    def teachersbyname(self, request, tl, one, two, module, extra, prog):
        
        def cmpsort(one,other):
            one_name = one['user'].last_name.upper()
            other_name = other['user'].last_name.upper()
            cmp0 = cmp(one_name, other_name)
                
            if cmp0 != 0:
                return cmp0

            return cmp(one['name'].upper(), other['name'].upper())

        return self.teachersbyFOO(request, tl, one, two, module, extra, prog, cmpsort)

    @needs_admin
    def roomsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file = 'roomlist.html', extra_func = lambda x: {}):
        
        rooms = self.program.groupedClassrooms()
        rooms = filter(filt_exp, rooms)
        for s in rooms:
            extra_dict = extra_func(s)
            for key in extra_dict:
                setattr(s, key, extra_dict[key])
        rooms.sort(sort_exp)

        context = {'rooms': rooms, 'program': self.program}

        return render_to_response(self.baseDir()+template_file, request, (prog, tl), context)

    @aux_call
    @needs_admin
    def roomsbytime(self, request, tl, one, two, module, extra, prog):
        #   List of open classrooms, sorted by the first time they are available
        def filt(one):
            return one.available_any_time(self.program.anchor)
        
        def cmpsort(one, other):
            #   Find when available
            return cmp(one.available_times(self.program.anchor)[0], other.available_times(self.program.anchor)[0])

        return self.roomsbyFOO(request, tl, one, two, module, extra, prog, cmpsort, filt)
        

    @needs_admin
    def studentsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file = 'studentlist.html', extra_func = lambda x: {}):
        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self     }
        students = filter(filt_exp, filterObj.getList(ESPUser).distinct())
        for s in students:
            extra_dict = extra_func(s)
            for key in extra_dict:
                setattr(s, key, extra_dict[key])
        students.sort(sort_exp)
        context['students'] = students
        
        return render_to_response(self.baseDir()+template_file, request, (prog, tl), context)

    @aux_call
    @needs_admin
    def studentsbyname(self, request, tl, one, two, module, extra, prog):
        """ default function to get student list for program """
        return self.studentsbyFOO(request, tl, one, two, module, extra, prog)

    @aux_call
    @needs_admin
    def emergencycontacts(self, request, tl, one, two, module, extra, prog):
        """ student list, having emergency contact information instead """
        from esp.program.models import RegistrationProfile
        
        def emergency_stuff(student):
            #  Try to get some kind of emergency contact info even if it wasn't entered for this program.
            program_profile = RegistrationProfile.getLastForProgram(student, prog)
            if program_profile.contact_emergency:
                return {'emerg_contact': program_profile.contact_emergency}
            else:
                other_profiles = RegistrationProfile.objects.filter(user=student).order_by('-last_ts')
                for prof in other_profiles:
                    if prof.contact_emergency:
                        return {'emerg_contact': prof.contact_emergency}
                
                return {}
        
        return self.studentsbyFOO(request, tl, one, two, module, extra, prog, template_file = 'studentlist_emerg.html', extra_func = emergency_stuff)

    @aux_call
    @needs_admin
    def students_lineitem(self, request, tl, one, two, module, extra, prog):
        from esp.accounting_core.models import LineItem
        #   Determine line item
        student_ids = []
        if request.GET.has_key('id'):
            lit_id = request.GET['id']
            request.session['li_type_id'] = lit_id
        else:
            lit_id = request.session['li_type_id']

        line_items = LineItem.objects.filter(li_type__id=lit_id)
        for l in line_items:
            student_ids.append(l.transaction.document_set.all()[0].user.id)

        return self.studentsbyFOO(request, tl, one, two, module, extra, prog, filt_exp = lambda x: x.id in student_ids)

    @aux_call
    @needs_admin
    def teacherschedules(self, request, tl, one, two, module, extra, prog):
        """ generate teacher schedules """

        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self     }
        teachers = list(filterObj.getList(ESPUser).distinct())
        teachers.sort()

        scheditems = []

        for teacher in teachers:
            # get list of valid classes
            classes = [ cls for cls in teacher.getTaughtSections()
                    if cls.parent_program == self.program
                    and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()            
            for cls in classes:
                scheditems.append({'name': teacher.name(),
                                   'teacher': teacher,
                                   'cls' : cls})

        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'teacherschedule.html', request, (prog, tl), context)

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        
        if key == 'receipt':
            #   Take the user's most recent registration profile.
            from django.template import Template
            from esp.middleware.threadlocalrequest import AutoRequestContext as Context
            from django.template.loader import find_template_source
            from django.conf import settings   
            prof = user.getLastProfile()
            
            li_types = prof.program.getLineItemTypes(user)
            
            # get program anchor or that of parent program
            p_anchor = prof.program.anchor
            if prof.program.getParentProgram():
                p_anchor = prof.program.getParentProgram().anchor
            try:
                invoice = Document.get_invoice(user, p_anchor, li_types, dont_duplicate=True, get_complete=True)
            except MultipleDocumentError:
                invoice = Document.get_invoice(user, p_anchor, li_types, dont_duplicate=True)
            
            context_dict = {'prog': prof.program, 'first_name': user.first_name, 'last_name': user.last_name, 'username': user.username, 'e_mail': prof.contact_user.e_mail, 'schedule': ProgramPrintables.getSchedule(prof.program, user)}
            
            context_dict['itemizedcosts'] = invoice.get_items()
            context_dict['itemizedcosttotal'] = invoice.cost()
            context_dict['owe_money'] = ( context_dict['itemizedcosttotal'] != 0 )
            
            t = Template(open(settings.TEMPLATE_DIRS + '/program/receipts/' + str(prof.program.id) + '_custom_receipt.txt').read())
            c = Context(context_dict)
            result_str = t.render(c)

            return result_str
            
        if key == 'schedule':
            #   Generic schedule function kept for backwards compatibility
            return ProgramPrintables.getSchedule(self.program, user)
        elif key == 'student_schedule':
            return ProgramPrintables.getSchedule(self.program, user, 'Student')
        elif key == 'student_schedule_norooms':
            return ProgramPrintables.getSchedule(self.program, user, 'Student', room_numbers=False)
        elif key == 'teacher_schedule':
            return ProgramPrintables.getSchedule(self.program, user, 'Teacher')
        elif key == 'volunteer_schedule':
            return ProgramPrintables.getSchedule(self.program, user, 'Volunteer')
        elif key == 'transcript':
            return ProgramPrintables.getTranscript(self.program, user, 'text')
        elif key == 'transcript_html':
            return ProgramPrintables.getTranscript(self.program, user, 'html')
        elif key == 'transcript_latex':
            return ProgramPrintables.getTranscript(self.program, user, 'latex')

        return ''

    @staticmethod
    def get_student_classlist(program, student):
        # get list of valid classes
        classes = [ cls for cls in student.getEnrolledSections()]
        classes = [ cls for cls in classes
                    if cls.parent_program == program
                    and cls.isAccepted()                       ]
        classes.sort()
        return classes

    @staticmethod
    def get_teacher_classlist(program, teacher):
        # get list of valid classes
        classes = [ cls for cls in teacher.getTaughtSections()]
        classes = [ cls for cls in classes
                    if cls.parent_program == program
                    and cls.isAccepted()                       ]
        classes.sort()
        return classes

    @staticmethod
    def getTranscript(program, student, format='text'):
        from django.template import Template
        from esp.middleware.threadlocalrequest import AutoRequestContext as Context
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
    def getSchedule(program, user, schedule_type=None, room_numbers=True):
        
        if schedule_type is None:
            if user.isStudent():
                schedule_type = 'Student'
            elif user.isTeacher():
                schedule_type = 'Teacher'
            elif user.isVolunteer():
                schedule_type = 'Volunteer'
            
        schedule = ''
        if schedule_type in ['Student', 'Teacher']:
            if room_numbers:
                schedule = """
    %s schedule for %s:

     Time                   | Class                                  | Room\n""" % (schedule_type, user.name())
            else:
                schedule = """
    %s schedule for %s:

     Time                   | Class                                  \n""" % (schedule_type, user.name())
            schedule += '------------------------+---------------------------------------------------\n'
            if schedule_type == 'Student':
                classes = ProgramPrintables.get_student_classlist(program, user)
            elif schedule_type == 'Teacher':
                classes = ProgramPrintables.get_teacher_classlist(program, user)
            for cls in classes:
                rooms = cls.prettyrooms()
                if len(rooms) == 0:
                    rooms = ' N/A'
                else:
                    rooms = ' ' + ", ".join(rooms)
                if room_numbers:
                    schedule += '%s|%s|%s\n' % ((' '+",".join(cls.friendly_times())).ljust(24), (' ' + cls.title()).ljust(40), rooms)
                else:
                    schedule += '%s|%s\n' % ((' '+",".join(cls.friendly_times())).ljust(24), (' ' + cls.title()).ljust(40))
                
        elif schedule_type == 'Volunteer':
            schedule = """
Volunteer schedule for %s:

 Time                   | Shift                                  \n""" % (user.name())
            schedule += '------------------------+----------------------------------------\n'
            shifts = user.volunteeroffer_set.filter(request__program=program).order_by('request__timeslot__start')
            for shift in shifts:
                schedule += ' %s| %s\n' % (shift.request.timeslot.pretty_time().ljust(23), shift.request.timeslot.description.ljust(39))

        return schedule

    @aux_call
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

    @aux_call
    @needs_admin
    def student_financial_spreadsheet(self, request, tl, one, two, module, extra, prog, onsite=False):
        if onsite:
            students = [ESPUser(User.objects.get(id=request.GET['userid']))]
        else:
            filterObj, found = UserSearchController().create_filter(request, self.program)
    
            if not found:
                return filterObj

            students = list(ESPUser.objects.filter(filterObj.get_Q()).distinct())

        import csv
        from django.http import HttpResponse
        response = HttpResponse(mimetype='text/csv')
        writer = csv.writer(response)

        for student in students:            
            li_types = prog.getLineItemTypes(student)
            try:
                invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True, get_complete=True)
            except MultipleDocumentError:
                invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True)

            writer.writerow((invoice.locator, student.id, student.last_name.encode('ascii', 'replace'), student.first_name.encode('ascii', 'replace'), invoice.cost()))
                
        return response
        
    @aux_call
    @needs_onsite_no_switchback
    def studentschedules(self, request, tl, one, two, module, extra, prog, onsite=False):
        
        context = {'module': self }

        if onsite:
            students = [ESPUser(User.objects.get(id=request.GET['userid']))]
        else:
            filterObj, found = UserSearchController().create_filter(request, self.program)
    
            if not found:
                return filterObj

            students = list(ESPUser.objects.filter(filterObj.get_Q(restrict_to_active=False)).distinct())

        students.sort()
        
        return ProgramPrintables.get_student_schedules(request, students, prog, extra, onsite)

    @staticmethod
    def get_student_schedules(request, students, prog, extra='', onsite=False):
        """ generate student schedules """
 
        context = {}
 
        scheditems = []
        
        # get the list of students who are in the parent program.
        parent_program_students_classreg = None
        parent_program = prog.getParentProgram()
        if parent_program is not None:
            parent_program_students = parent_program.students()
            if parent_program_students.has_key('classreg'):
                parent_program_students_classreg = parent_program_students['classreg']
        
        all_events = Event.objects.filter(anchor=prog.anchor).order_by('start')
        for student in students:
            student.updateOnsite(request)
            # get list of valid classes
            classes = [ cls for cls in student.getEnrolledSections()
                                if cls.parent_program == prog and cls.isAccepted() and cls.meeting_times.count() > 0]
            # now we sort them by time/title
            classes.sort()

            if Tag.getTag('studentschedule_show_empty_blocks', target=prog):
                #   If you want to show empty blocks, start with a list of blocks instead
                #   and replace with classes where appropriate.
                times = list(prog.getTimeSlots())
                for cls in classes:
                    time_indices = []
                    index = 0
                    for t in cls.meeting_times.all():
                        if t in times:
                            index = times.index(t)
                            times.remove(t)
                    times.insert(index, cls)
                classes = times

            #   Insert entries for the compulsory timeblocks into the schedule
            min_index = 0
            times_compulsory = Event.objects.filter(anchor=prog.anchor, event_type__description='Compulsory').order_by('start')
            for t in times_compulsory:
                i = min_index
                while i < len(classes):
                    if classes[i].start_time().start > t.start:
                        classes.insert(i, t)
                        break
                    i += 1
                min_index = i
                
            # note whether student is in parent program
            student.in_parent_program = False
            if parent_program_students_classreg is not None:
                # we use the filter instead of simply "in" because the types of items in "students" and "parent_program_students_classreg" don't match.
                student.in_parent_program = parent_program_students_classreg.filter(id=student.id).count() > 0
            
            # get payment information
            li_types = prog.getLineItemTypes(student)
            try:
                invoice = Document.get_invoice(student, prog.anchor, li_types, dont_duplicate=True, get_complete=True)
            except MultipleDocumentError:
                invoice = Document.get_invoice(student, prog.anchor, li_types, dont_duplicate=True)
            
            # attach payment information to student
            student.invoice_id = invoice.locator
            student.itemizedcosts = invoice.get_items()
            student.meals = student.itemizedcosts.filter(li_type__anchor__parent__name__in=('Optional','BuyMultiSelect')).distinct()  # catch everything that's not admission to the program.
            student.admission = student.itemizedcosts.filter(li_type__anchor__name='Required').distinct()  # Program admission
            student.paid_online = student.itemizedcosts.filter(anchor__parent__name='Receivable').distinct()  # LineItems for having paid online.
            student.itemizedcosttotal = invoice.cost()
            
            # check financial aid
            student.has_financial_aid = student.hasFinancialAid(prog.anchor)
            if student.has_financial_aid and not student.itemizedcosts.filter(li_type__text=u'Financial Aid', amount__gt=0).distinct().count() and not student.itemizedcosts.filter(anchor__uri=prog.anchor.uri+"/Accounts/FinancialAid", amount__gt=0).distinct().count():
                apps = FinancialAidRequest.objects.filter(user=student, program=prog, approved__isnull=False).distinct()
                aid = max(list(apps.values_list('amount_received', flat=True).distinct()))
                if aid:
                    student.itemizedcosttotal -= aid
                else:
                    student.itemizedcosttotal = 0.0

            # add cost/credit information from SplashInfo (looks in JSON Tag: splashinfo_costs)
            student.splashinfo = SplashInfo.getForUser(student, prog)
            if student.splashinfo:
                tag_data = Tag.getTag('splashinfo_costs', target=prog)
                if not tag_data: tag_data = Tag.getTag('splashinfo_costs')
                if tag_data:
                    tag_struct = json.loads(tag_data)
                    for key in tag_struct:
                        val = getattr(student.splashinfo, key)
                        if val in tag_struct[key] and not student.has_financial_aid:
                            student.itemizedcosttotal += Decimal(str(tag_struct[key][val]))
                if student.splashinfo.siblingdiscount:
                    amt_str = Tag.getTag('splashinfo_sibling_discount')
                    if not amt_str:
                        amt_str = '20.0'
                    if not student.has_financial_aid:
                        student.itemizedcosttotal -= Decimal(amt_str)

            student.has_paid = ( student.itemizedcosttotal == 0 )
            
            # MIT Splash purchase counts; temporary, should be harmless
            student.shirtcount = student.meals.filter(text__contains='T-shirt').count()
            student.photocount = student.meals.filter(text__contains='Photo').count()
            student.saturday_lunch = student.meals.filter(text__contains='Saturday Lunch').count()
            student.sunday_lunch = student.meals.filter(text__contains='Sunday Lunch').count()
            student.saturday_dinner = student.meals.filter(text__contains='Saturday Dinner').count()

            student.payment_info = True
            student.classes = classes
            
        context['students'] = students
        context['program'] = prog
        
        if extra:
            file_type = extra.strip()
        elif 'img_format' in request.GET:
            file_type = request.GET['img_format']
        else:
            file_type = 'pdf'

        if onsite and file_type == 'pdf':
            file_type = 'png'

        from django.conf import settings
        context['PROJECT_ROOT'] = settings.PROJECT_ROOT.rstrip('/') + '/'
    
        basedir = 'program/modules/programprintables/'
        if file_type == 'html':
            return render_to_response(basedir+'studentschedule.html', request, (prog, tl), context)
        else:  # elif format == 'pdf':
            from esp.web.util.latex import render_to_latex
            schedule_template = select_template([basedir+'program_custom_schedules/%s_studentschedule.tex' %(prog.id), basedir+'studentschedule.tex'])
            return render_to_latex(schedule_template, context, file_type)

    @aux_call
    @needs_admin
    def flatstudentschedules(self, request, tl, one, two, module, extra, prog):
        """ generate student schedules """

        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self }
        students = list(ESPUser.objects.filter(filterObj.get_Q()).distinct())

        students.sort()
        
        scheditems = []

        for student in students:
            # get list of valid classes
            classes = [ cls for cls in student.getEnrolledSections()
                    if cls.parent_program == self.program
                    and cls.isAccepted()                       ]
            # now we sort them by time/title
            classes.sort()
            
            for cls in classes:
                scheditems.append({'name': student.name(),
                                   'cls' : cls})

        context['scheditems'] = scheditems

        from django.conf import settings
        context['PROJECT_ROOT'] = settings.PROJECT_ROOT.rstrip('/') + '/'
        
        return render_to_response(self.baseDir()+'flatstudentschedule.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def roomschedules(self, request, tl, one, two, module, extra, prog):
        """ generate class room rosters"""
        from esp.cal.models import Event
        
        classes = list(self.program.sections().filter(status=10, parent_class__status=10))

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
            rooms[room_name].sort(key=lambda x: x['timeblock'].start)
            for val in rooms[room_name]:
                scheditems.append(val)
                
        context['scheditems'] = scheditems
        context['settings'] = settings
        context['group_name'] = Tag.getTag('full_group_name')
        context['phone_number'] = Tag.getTag('group_phone_number')

        return render_to_response(self.baseDir()+'roomrosters.html', request, (prog, tl), context)            

    @aux_call
    @needs_admin
    def student_tickets(self, request, tl, one, two, module, extra, prog):
        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj
        
        students = ESPUser.objects.filter(filterObj.get_Q()).distinct().order_by('last_name')
        lastnames = students.values_list('last_name')
        num_lastnames = len(lastnames)
        context = {'name_groups': []}

        try:
            context['colors'] = request.GET['colors'].split(',')
        except:
            context['colors'] = ['Yellow', 'Blue', 'Pink', 'Green', 'Turquoise', 'Purple', 'Yellow', 'Blue']
        
        get_data = request.GET.copy()
        try:
            name_groups = get_data['name_groups']
        except:
            name_groups = 'a,c,e,h,k,o,s,u'
            get_data['name_groups'] = name_groups
            

        if 'name_groups' in get_data:
            name_group_start = get_data['name_groups'].split(',')
            for i in range(len(name_group_start)):
                gs = name_group_start[i]
                if i < len(name_group_start) - 1:
                    gs_end = name_group_start[i + 1]
                    context['name_groups'].append(students.filter(last_name__gte=gs, last_name__lt=gs_end))
                else:
                    context['name_groups'].append(students.filter(last_name__gte=gs))
                    
        else:

            try:
                num_name_groups = int(extra)
            except:
                num_name_groups = 7
            
            names_per_set = float(num_lastnames) / num_name_groups
            for i in range(num_name_groups):
                start_index = int(i * names_per_set)
                end_index = int((i + 1) * names_per_set)
                context['name_groups'].append(students[start_index:end_index])

        num_per_page = 12
        student_tuples = []
        #   Make an ordered list of all students
        for i in range(len(context['name_groups'])):
            color = context['colors'][i]
            line_num = i + 1
            for item in context['name_groups'][i]:
                student_tuples.append((line_num, color, item))
        num_students = len(student_tuples)
        num_pages = (num_students - 1) / num_per_page + 1
        pages = [[] for i in range(num_pages)]
        #   Deal the list out into pages of [num_per_page] stacks
        for i in range(num_students):
            pages[i % num_pages].append(student_tuples[i])

        context['pages'] = pages

        return render_to_response(self.baseDir()+'student_tickets.html', request, (prog, tl), context)
    
    @aux_call
    @needs_admin
    def classrosters(self, request, tl, one, two, module, extra, prog):
        """ generate class rosters """


        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj



        context = {'module': self     }
        teachers = list(ESPUser.objects.filter(filterObj.get_Q()).distinct())
        teachers.sort()

        scheditems = []

        for teacher in teachers:
            for cls in teacher.getTaughtClasses(self.program):
                if cls.isAccepted():
                    scheditems.append({'teacher': teacher,
                                       'cls'    : cls})

        context['scheditems'] = scheditems
        if extra == 'attendance':
            tpl = 'classattendance.html'
        else:
            tpl = 'classrosters.html'
        
        return render_to_response(self.baseDir()+tpl, request, (prog, tl), context)
        
    @aux_call
    @needs_admin
    def teacherlabels(self, request, tl, one, two, module, extra, prog):
        context = {'module': self}
        teachers = list(self.program.teachers()['class_approved'])
        teachers.sort()
        context['teachers'] = teachers
        context['settings'] = settings
        return render_to_response(self.baseDir()+'teacherlabels.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def studentchecklist(self, request, tl, one, two, module, extra, prog):
        context = {'module': self}
        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj


        students = list(ESPUser.objects.filter(filterObj.get_Q()).distinct())
        students.sort()

        studentList = []
        for student in students:
            paid_symbol = ''
            finaid_status = 'None'
            if student.appliedFinancialAid(prog):
                if student.financialaidrequest_set.filter(program=prog).order_by('-id')[0].reduced_lunch:
                    finaid_status = 'Req. (RL)'
                else:
                    finaid_status = 'Req. (No RL)'
            
            if student.hasFinancialAid(self.program_anchor_cached()):
                paid_symbol = 'X'
                finaid_status = 'Approved'
            else:
                li_types = prog.getLineItemTypes(student)
                try:
                    invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True, get_complete=True)
                except MultipleDocumentError:
                    invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True)
                if invoice.cost() == 0:
                    paid_symbol = 'X'

            studentList.append({'user': student, 'paid': paid_symbol, 'finaid': finaid_status})

        context['students'] = students
        context['studentList'] = studentList
        return render_to_response(self.baseDir()+'studentchecklist.html', request, (prog, tl), context)

    @aux_call
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
            class_dict = {'cls': c}
            student_list = []
            
            for student in students:
                if c in student.getEnrolledClasses(self.program):
                    paid_symbol = ''
                    if student.hasFinancialAid(self.program_anchor_cached()):
                        paid_symbol = 'X'
                    else:
                        li_types = prog.getLineItemTypes(student)
                        try:
                            invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True, get_complete=True)
                        except MultipleDocumentError:
                            invoice = Document.get_invoice(student, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True)
                        if invoice.cost() == 0:
                            paid_symbol = 'X'
                    
                    student_list.append({'user': student, 'paid': paid_symbol})
            
            class_dict['students'] = student_list
            class_list.append(class_dict)

        context['class_list'] = class_list
        
        return render_to_response(self.baseDir()+'classchecklists.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def adminbinder(self, request, tl, one, two, module, extra, prog):
        
        if extra not in ['teacher','classid','timeblock']:
            return self.goToCore(tl)
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

            classes.sort(ClassSubject.idcmp)

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

    @aux_call
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
        
    @aux_call
    @needs_admin
    def all_classes_spreadsheet(self, request, tl, one, two, module, extra, prog):
        import csv
        from django.http import HttpResponse
        from django.utils.encoding import smart_str

        response = HttpResponse(mimetype="text/csv")
        write_cvs = csv.writer(response)

        write_cvs.writerow(("ID", "Teachers", "Title", "Duration", "GradeMin", "GradeMax", "ClsSizeMin", "ClsSizeMax", "Category", "Class Info", "Requests", "Msg for Directors", "Prereqs", "Directors Notes", "Assigned Times", "Assigned Rooms"))
        for cls in ClassSubject.objects.filter(parent_program=prog):
            write_cvs.writerow(
                (cls.id,
                 ", ".join([smart_str(t.name()) for t in cls.teachers()]),
                 smart_str(cls.title()),
                 cls.prettyDuration(),
                 cls.grade_min,
                 cls.grade_max,
                 cls.class_size_min,
                 cls.class_size_max,
                 cls.category,
                 smart_str(cls.class_info),
                 ", ".join(set(x.res_type.name for x in cls.getResourceRequests())),
                 smart_str(cls.message_for_directors),
                 smart_str(cls.prereqs),
                 smart_str(cls.directors_notes),
                 ", ".join(cls.friendly_times()),
                 ", ".join(cls.prettyrooms()),
                 ))

        response['Content-Disposition'] = 'attachment; filename=all_classes.csv'
        return response

    @aux_call
    @needs_admin
    def oktimes_spr(self, request, tl, one, two, module, extra, prog):
        """
        Create a spreadsheet with all classes, with info and the times
        at which they can be scheduled to start.

        An extra argument of 'unscheduled' shows only the currently-
        unscheduled classes, taking into account the classes the teacher
        is already teaching and have been scheduled.
        """
        import csv
        from django.http import HttpResponse

        response = HttpResponse(mimetype="text/csv")
        write_csv = csv.writer(response)

        # get the list of all the sections, and all the times for this program.
        sections = prog.sections().order_by('-parent_class__class_size_max')

        # get only the unscheduled sections, rather than all of them
        # also, only approved classes in the spreadsheet; can be changed
        if extra == "unscheduled":
            sections = sections.filter(meeting_times__isnull=True, status=10)

        times = prog.getTimeSlots()
        if extra == "unscheduled":
            sections_possible_times = [(section, section.viable_times(True)) for section in sections]
        else:
            sections_possible_times = [(section, section.viable_times(False)) for section in sections]

        # functions to determine what will fill in the spreadsheet cell for each thing
        def time_possible(time, sections_list):
            if time in sections_list:
                return 'X'
            else:
                return ' '
        def needs_resource(resname, section):
            if section.getResourceRequests().filter(res_type__name=resname):
                return 'Y'
            else:
                return ' '

        if Tag.getTag('oktimes_collapse'):
            time_headers = ['Feasible Start Times']
        else:
            time_headers = [str(time) for time in times]

        # header row, naming each column
        write_csv.writerow(['ID', 'Code', 'Title', 'Duration'] + ['Teachers'] + ['Projector?'] + \
                           ['Computer Lab?'] + ['Resource Requests'] + ['Optimal Size'] + \
                           ['Max Size'] + \
                           ['Grade Levels'] + ['Comments to Director'] + \
                           ['Assigned Time'] + ['Assigned Room'] + \
                           time_headers)

        # this writes each row associated with a section, for the columns determined above.
        for section, timeslist in sections_possible_times:
            if Tag.getTag('oktimes_collapse'):
                time_values = [', '.join([e.start.strftime('%a %I:%M %p') for e in section.viable_times()])]
            else:
                time_values = [time_possible(time, timeslist) for time in times]    
        
            write_csv.writerow([section.id, section.emailcode(), smart_str(section.title()), section.prettyDuration()] + \
                               [smart_str(section.parent_class.pretty_teachers())] + \
                               [needs_resource('LCD Projector', section)] + \
                               [needs_resource('Computer Lab', section)] + \
                               [', '.join(['%s: %s' % (r.res_type.name, r.desired_value) for r in section.getResourceRequests()])] + \
                               [section.parent_class.class_size_optimal] + \
                               [section.parent_class.class_size_max] + \
                               ['%d--%d' %(section.parent_class.grade_min, section.parent_class.grade_max)] +\
                               [smart_str(section.parent_class.message_for_directors)] + \
                               [", ".join(section.friendly_times())] + [", ".join(section.prettyrooms())] + \
                               time_values)
                               
        response['Content-Disposition'] = 'attachment; filename=ok_times.csv'
        return response

    @aux_call
    @needs_admin
    def concise_oktimes_spr(self, request, tl, one, two, module, extra, prog):
        """
        Create a concise spreadsheet with one row per class (not per section), with info and the times
        at which they can be scheduled to start.  This is useful for printing out for scheduling.

        class number
        hours
        sections
        classroom and equipment requests
        viable starting times
        conflicts (other classes taught by same teacher)
        room requests and comments
        """
        import csv
        from django.http import HttpResponse
        from esp.resources.models import ResourceType

        response = HttpResponse(mimetype="text/csv")
        write_csv = csv.writer(response)

        # get first section of each class
        sections = [section for section in prog.sections().order_by('parent_class') if section.index() == 1]

        # get only the unscheduled sections, rather than all of them
        # also, only approved classes in the spreadsheet; can be changed
        #if extra == "unscheduled":
        #    sections = sections.filter(meeting_times__isnull=True, status=10)

        times = prog.getTimeSlots()
        if extra == "unscheduled":
            sections_possible_times = [(section, section.viable_times(True)) for section in sections]
        else:
            sections_possible_times = [(section, section.viable_times(False)) for section in sections]

        # functions to determine what will fill in the spreadsheet cell for each thing
        def time_possible(time, sections_list):
            if time in sections_list:
                return 'X'
            else:
                return ' '

        time_headers = [str(time) for time in times]

        # get all resource types
        resource_types = ResourceType.objects.filter(program=prog)
        resource_headers = [resource_type.description for resource_type in resource_types]

        # header row, naming each column
        write_csv.writerow(['Code', 'Hours'] + ['Sections'] + ['Size'] + resource_headers +\
                           time_headers +  \
                           ['Conflicts'] + \
                           ['Comments'])

        # this writes each row associated with a section, for the columns determined above.
        for section, timeslist in sections_possible_times:
            time_values = [time_possible(time, timeslist) for time in times]

            # get conflicts
            teachers = section.parent_class.teachers()
            conflicts = []
            for teacher in teachers:
                conflicts.extend(filter(lambda x: x not in conflicts and x != section.parent_class, teacher.getTaughtClassesFromProgram(prog)))
            conflicts = sorted(conflicts, key = lambda x: x.id)

            write_csv.writerow([section.parent_class.emailcode(), int(round(section.duration))] + \
                               [str(len(section.parent_class.get_sections()))] + \
                               [section.parent_class.class_size_max] + \
                               [', '.join([r.desired_value for r in section.getResourceRequests() if r.res_type == rt]) for rt in resource_types]+ \
                               time_values + \
                               [', '.join([conflict.emailcode() for conflict in conflicts])]  + \
                               [smart_str(((section.parent_class.requested_room + '. ') if section.parent_class.requested_room else '') + section.parent_class.message_for_directors)])

        response['Content-Disposition'] = 'attachment; filename=ok_times_concise.csv'
        return response

    @aux_call
    @needs_admin
    def csv_schedule(self, request, tl, one, two, module, extra, prog):
        """ A CSV-formatted list of existing schedule assignments, intended to
            be used as initial conditions for automatic scheduling.  The response
            has 4 columns:
                -   ID of the class section
                -   Name of the classroom
                -   ID of the timeslot
                -   Lock level (usually 0 for unlocked, 1 or higher for locked)
        """
        import csv
        from django.http import HttpResponse
        from esp.resources.models import ResourceAssignment
        response = HttpResponse(mimetype="text/csv")
        write_csv = csv.writer(response)
        
        data = ResourceAssignment.objects.filter(target__parent_class__parent_program=prog).order_by('target__id', 'resource__event__id').values_list('target__id', 'resource__name', 'resource__event__id', 'lock_level')
        for row in data:
            write_csv.writerow(row)
        
        response['Content-Disposition'] = 'attachment; filename=csv_schedule.csv'
        return response

    class Meta:
        abstract = True

