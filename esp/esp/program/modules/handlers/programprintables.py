
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
  Email: web-team@learningu.org
"""
from esp.program.modules.base import ProgramModuleObj, needs_admin, needs_onsite_no_switchback, main_call, aux_call
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser, User, Record
from esp.program.models  import ClassSubject, ClassSection, StudentRegistration
from esp.program.models  import ClassFlagType
from esp.program.models.class_ import ACCEPTED
from esp.users.views     import search_for_user
from esp.users.controllers.usersearch import UserSearchController
from esp.utils.latex  import render_to_latex
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.tagdict.models import Tag
from esp.cal.models import Event
from esp.middleware import ESPError
from esp.utils.query_utils import nest_Q
from esp.program.models import VolunteerOffer
from esp.survey.views import _encode_ascii

from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.db.models import IntegerField, Case, When, Count
from django.template import Context, loader
from django.template.loader import render_to_string, get_template
from django.utils.encoding import smart_str
from django.utils.html import mark_safe

from decimal import Decimal
import json
import collections
import copy
import csv

class ProgramPrintables(ProgramModuleObj):
    """ This is extremely useful for printing a wide array of documents for your program.
    Things from checklists to rosters to attendance sheets can be found here. """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Program Printables",
            "module_type": "manage",
            "seq": 5,
            "choosable": 1,
            }

    @aux_call
    @needs_admin
    def paid_list_filter(self, request, tl, one, two, module, extra, prog):
        pac = ProgramAccountingController(prog)
        lineitemtypes = pac.get_lineitemtypes(optional_only=True)
        context = { 'lineitemtypes': lineitemtypes }
        return render_to_response(self.baseDir()+'paid_list_filter.html', request, context)

    @aux_call
    @needs_admin
    def paid_list(self, request, tl, one, two, module, extra, prog):
        pac = ProgramAccountingController(prog)
        if 'filter' in request.GET:
            try:
                ids = [ int(x) for x in request.GET.getlist('filter') ]
                single_select = ( len(ids) == 1 )
            except ValueError:
                ids = None
                single_select = False

            if ids == None:
                transfers = pac.all_transfers(optional_only=True).order_by('line_item','user').select_related()
            else:
                lineitems = pac.all_transfers(optional_only=True).filter(line_item__id__in=ids).order_by('line_item','user').select_related()
        else:
            single_select = False
            lineitems = pac.all_transfers(optional_only=True).order_by('line_item','user').select_related()

        for lineitem in lineitems:
            lineitem.has_financial_aid = lineitem.user.hasFinancialAid(prog)

        def sort_fn(a,b):
            if a.user.last_name.lower() > b.user.last_name.lower():
                return 1
            return -1

        lineitems_list = list(lineitems)
        lineitems_list.sort(sort_fn)

        context = { 'lineitems': lineitems_list,
                    'hide_paid': request.GET.get('hide_paid') == 'True',
                    'prog': prog,
                    'single_select': single_select }

        return render_to_response(self.baseDir()+'paid_list.html', request, context)

    @main_call
    @needs_admin
    def printoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self, 'li_types': prog.getLineItemTypes(required=False)}

        return render_to_response(self.baseDir()+'options.html', request, context)

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

        if request.GET.get('first_sort', ''):
            sort_list.append( cmp_fn[request.GET['first_sort']] )
            sort_name_list.append( request.GET['first_sort'] )
        else:
            sort_list.append( cmp_fn["category"] )

        if request.GET.get('second_sort', ''):
            sort_list.append( cmp_fn[request.GET['second_sort']] )
            sort_name_list.append( request.GET['second_sort'] )
        else:
            sort_list.append( cmp_fn["timeblock"] )

        if request.GET.get('third_sort', ''):
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

        if 'ids' in request.GET and 'op' in request.GET and \
           'clsid' in request.GET:
            try:
                clsid = int(request.GET['clsid'])
                cls   = ClassSubject.objects.get(parent_program = self.program,
                                          id             = clsid)
            except:
                raise ESPError('Could not get the class object.')

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
                raise ESPError('Received invalid operation for class list.')

            classes = []

            for clsid in clsids:
                classes.append(cls_dict[clsid])

            clsids = ','.join(clsids)
            return render_to_response(self.baseDir()+'catalog_order.html',
                                      request,
                                      {'clsids': clsids, 'classes': classes, 'sorting_options': cmp_fn.keys(), 'sort_name_list': ",".join(sort_name_list), 'sort_name_list_orig': sort_name_list, 'category_options': category_options, 'grade_options': grade_options, 'grade_min_orig': grade_min, 'grade_max_orig': grade_max, 'categories_orig': categories })

        if "only_nonfull" in request.GET:
            classes = [x for x in classes if not x.isFull()]

        sort_list_reversed = sort_list
        sort_list_reversed.reverse()
        for sort_fn in sort_list_reversed:
            classes.sort(sort_fn)

        clsids = ','.join([str(cls.id) for cls in classes])

        return render_to_response(self.baseDir()+'catalog_order.html',
                                  request,
                                  {'clsids': clsids, 'classes': classes, 'sorting_options': cmp_fn.keys(), 'sort_name_list': ",".join(sort_name_list), 'sort_name_list_orig': sort_name_list, 'category_options': category_options, 'grade_options': grade_options, 'grade_min_orig': grade_min, 'grade_max_orig': grade_max, 'categories_orig': categories  })


    @aux_call
    @needs_admin
    def coursecatalog(self, request, tl, one, two, module, extra, prog):
        " This renders the course catalog in LaTeX. "
        from django.conf import settings
        classes = ClassSubject.objects.filter(parent_program = self.program)

        if 'mingrade' in request.GET:
            mingrade=int(request.GET['mingrade'])
            classes = classes.filter(grade_max__gte=mingrade)

        if 'maxgrade' in request.GET:
            maxgrade=int(request.GET['maxgrade'])
            classes = classes.filter(grade_min__lte=maxgrade)

        if 'open' in request.GET:
            classes = [cls for cls in classes if not cls.isFull()]

        if request.GET.get('sort_name_list'):
            sort_order = request.GET['sort_name_list'].split(',')
        else:
            sort_order = Tag.getProgramTag('catalog_sort_fields', prog, default='category').split(',')

        #   Perform sorting based on specified order rules
        #   NOTE: Other catalogs can filter by _num_students but this one can't.
        if '_num_students' in sort_order:
            sort_order.remove('_num_students')
        #   Replace incorrect 'timeblock' sort field with sorting by meeting times start field.
        for i in xrange(len(sort_order)):
            if sort_order[i] == 'timeblock':
                sort_order[i] = 'meeting_times__start'
        classes = classes.order_by(*sort_order)

        #   Filter out classes that are not scheduled
        classes = [cls for cls in classes
                   if cls.isAccepted() and cls.sections.all().filter(meeting_times__isnull=False).exists() ]

        #   Filter out duplicate classes in case sort order causes extra results
        unique_classes = []
        ids_existing = []
        for cls in classes:
            if cls.id not in ids_existing:
                unique_classes.append(cls)
                ids_existing.append(cls.id)
        classes = unique_classes

        #   Reorder classes if an ordering was specified by request.GET['clsids']
        if 'clsids' in request.GET:
            clsids = request.GET['clsids'].split(',')
            cls_dict = {}
            for cls in classes:
                cls_dict[str(cls.id)] = cls
            classes = [cls_dict[clsid] for clsid in clsids if clsid in cls_dict]

        context = {'classes': classes, 'program': self.program}

        group_name = Tag.getTag('full_group_name')
        if not group_name:
            group_name = '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        context['group_name'] = group_name

        #   Hack for timeblock sorting (sorting by category is the default)
        template_name = 'catalog_category.tex'
        if sort_order[0] == 'meeting_times__start':
            template_name = 'catalog_timeblock.tex'
            sections = []
            for cls in classes:
                sections += list(x for x in cls.sections.all().filter(status__gt=0, meeting_times__isnull=False).distinct() if not ('open' in request.GET and x.isFull()))
            sections.sort(key=lambda x: x.start_time())
            context['sections'] = sections

        if extra is None or len(str(extra).strip()) == 0:
            extra = 'pdf'

        return render_to_latex(self.baseDir()+template_name, context, extra)

    @aux_call
    @needs_admin
    def classpopularity(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(parent_program = prog)
        priorities = range(1, prog.studentclassregmoduleinfo.priority_limit + 1)

        # We'll get the SRs and SSIs separately because otherwise we're joining two potentially large tables in a single query,
        # which can result in an absurd number of rows for even moderate programs

        # Fetch class SRs
        sr_classes = classes
        for priority in priorities:
            sr_classes = sr_classes.annotate(**{'priority' + str(priority): Count(
            Case(When(sections__studentregistration__relationship__name='Priority/' + str(priority), then=1), default=None, output_field=IntegerField()
            ))})

        # Fetch class SSI
        ssi_classes = classes
        ssi_classes = ssi_classes.annotate(ssi=Count('studentsubjectinterest', distinct=True))

        # Merge the two (by ID)
        by_id = {}
        for subject in sr_classes:
            by_id[subject.id] = subject
        for subject in ssi_classes:
            if subject.id in by_id:
                by_id[subject.id].ssi = subject.ssi
            else:
                by_id[subject.id] = subject

        # Sort
        classes = sorted(by_id.values(), key=lambda s: s.ssi, reverse = True)

        context = {'classes': classes, 'program': prog, 'priorities': [str(priority) for priority in priorities]}

        return render_to_response(self.baseDir()+'classes_popularity.html', request, context)

    @aux_call
    @needs_admin
    def classflagdetails(self, request, tl, one, two, module, extra, prog):
        comments = 'comments' in request.GET
        classes = ClassSubject.objects.filter(parent_program = prog)
        if 'clsids' in request.GET:
            clsids = [int(clsid) for clsid in request.GET['clsids'].split(",")]
            classes = [cls for cls in classes if cls.id in clsids]
        if 'accepted' in request.GET:
            classes = [cls for cls in classes if cls.status > 0]
        elif 'cancelled' in request.GET:
            classes = [cls for cls in classes if cls.isCancelled()]
        elif 'all' not in request.GET:
            classes = [cls for cls in classes if cls.status >= 0]
        if 'scheduled' in request.GET:
            classes = [cls for cls in classes if cls.all_meeting_times.count() > 0]

        cls_list = []
        flag_types = ClassFlagType.get_flag_types(program=prog).order_by("seq")

        for cls in classes:
            flags = cls.flags.all()
            type_dict = {}
            for flag in flags:
                if flag.flag_type in type_dict:
                    type_dict[flag.flag_type].append(flag)
                else:
                    type_dict[flag.flag_type] = [flag]
            cls.flag_list = []
            for type in flag_types:
                if type in type_dict.keys():
                    comms = [flag.comment for flag in type_dict[type] if flag.comment]
                    if len(comms) > 0 and comments:
                        cls.flag_list.append(comms)
                    else:
                        cls.flag_list.append(True)
                else:
                    cls.flag_list.append(False)
            cls_list.append(cls)

        context = {'classes': cls_list, 'program': prog, 'flag_types': flag_types}

        return render_to_response(self.baseDir()+'classes_flags.html', request, context)

    @needs_admin
    def classesbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, split_teachers = False, template_file='classes_list.html'):
        classes = ClassSubject.objects.filter(parent_program = self.program)

        if 'clsids' in request.GET:
            clsids = [int(clsid) for clsid in request.GET['clsids'].split(",")]
            classes = [cls for cls in classes if cls.id in clsids]

        if 'grade_min' in request.GET:
            classes = [cls for cls in classes if cls.grade_max >= int(request.GET['grade_min'])]

        if 'grade_max' in request.GET:
            classes = [cls for cls in classes if cls.grade_min <= int(request.GET['grade_max'])]

        if 'accepted' in request.GET:
            classes = [cls for cls in classes if cls.status > 0]
        elif 'cancelled' in request.GET:
            classes = [cls for cls in classes if cls.isCancelled()]
        elif 'all' not in request.GET:
            classes = [cls for cls in classes if cls.status >= 0]

        if 'scheduled' in request.GET:
            classes = [cls for cls in classes if cls.all_meeting_times.count() > 0]

        classes = filter(filt_exp, classes)

        if split_teachers:
            classes_temp = []
            for cls in classes:
                for teacher in cls.get_teachers():
                    cls_split = copy.copy(cls)
                    cls_split.split_teacher = teacher
                    classes_temp.append(cls_split)
            classes = classes_temp

        classes.sort(sort_exp)

        context = {'classes': classes, 'program': self.program}

        if (extra and 'csv' in extra) or 'csv' in request.GET:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="classes_list.csv"'
            t = loader.get_template(self.baseDir()+'classes_list.csv')
            c = Context(context)
            response.write(t.render(c))
            return response
        else:
            return render_to_response(self.baseDir()+template_file, request, context)

    @needs_admin
    def sectionsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file='sections_list.html'):
        sections = self.program.sections()

        if 'secids' in request.GET:
            secids = [int(secid) for secid in request.GET['secids'].split(",")]
            sections = [sec for sec in sections if sec.id in secids]

        if 'clsids' in request.GET:
            clsids = [int(clsid) for clsid in request.GET['clsids'].split(",")]
            sections = [sec for sec in sections if sec.parent_class.id in clsids]

        if 'grade_min' in request.GET:
            sections = [sec for sec in sections if sec.parent_class.grade_max >= int(request.GET['grade_min'])]

        if 'grade_max' in request.GET:
            sections = [sec for sec in sections if sec.parent_class.grade_min <= int(request.GET['grade_max'])]

        if 'accepted' in request.GET:
            sections = [sec for sec in sections if sec.status > 0]
        elif 'cancelled' in request.GET or (extra and 'cancelled' in extra):
            sections = [sec for sec in sections if sec.isCancelled()]
        elif 'all' not in request.GET:
            sections = [sec for sec in sections if sec.status >= 0]

        if 'scheduled' in request.GET:
            sections = [sec for sec in sections if sec.meeting_times.count() > 0]

        sections = filter(filt_exp, sections)

        sections.sort(sort_exp)

        context = {'sections': sections, 'program': self.program}

        if (extra and 'csv' in extra) or 'csv' in request.GET:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sections_list.csv"'
            t = loader.get_template(self.baseDir()+'sections_list.csv')
            c = Context(context)
            response.write(t.render(c))
            return response
        else:
            return render_to_response(self.baseDir()+template_file, request, context)

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
            cmp0 = cmp(one.title.lstrip().strip('"\',.<![($'), other.title.lstrip().strip('"\',.<![($'))

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)

        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_title)

    @aux_call
    @needs_admin
    def classesbyteacher(self, request, tl, one, two, module, extra, prog):
        def cmp_teacher(one, other):
            cmp0 = cmp(one.split_teacher.last_name.lower(), other.split_teacher.last_name.lower())

            if cmp0 != 0:
                return cmp0

            return cmp(one, other)

        def filt_teacher(cls):
            return len(cls.get_teachers()) > 0

        return self.classesbyFOO(request, tl, one, two, module, extra, prog, cmp_teacher, filt_teacher, True)

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

    @needs_admin
    def teachersbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file = 'teacherlist.html', extra_func = lambda x: {}):
        from esp.users.models import ContactInfo

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

        if extra and 'secondday' in extra:
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

            if  extra and 'secondday' in extra:
                new_classes = []
                first_timeblock = first_timeblock_dict['meeting_times__start__min']

                for cls in classes:
                    starttime = cls.meeting_times.all().order_by('start')[0]
                    if (starttime.start.month, starttime.start.day) != \
                       (first_timeblock.month, first_timeblock.day):
                        new_classes.append(cls)

                classes = new_classes

            ci = ContactInfo.objects.filter(user=teacher, phone_cell__isnull=False, as_user__isnull=False).exclude(phone_cell='').distinct('user')
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

        if extra and 'csv' in extra:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="teacherlist.csv"'
            t = loader.get_template(self.baseDir()+'teacherlist.csv')
            c = Context(context)
            response.write(t.render(c))
            return response
        else:
            return render_to_response(self.baseDir()+template_file, request, context)

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

        return render_to_response(self.baseDir()+template_file, request, context)

    @aux_call
    @needs_admin
    def roomsbytime(self, request, tl, one, two, module, extra, prog):
        #   List of open classrooms, sorted by the first time they are available
        def filt(one):
            return one.available_any_time(self.program)

        def cmpsort(one, other):
            #   Find when available
            return cmp(one.available_times(self.program)[0], other.available_times(self.program)[0])

        return self.roomsbyFOO(request, tl, one, two, module, extra, prog, cmpsort, filt)


    @needs_admin
    def studentsbyFOO(self, request, tl, one, two, module, extra, prog, sort_exp = lambda x,y: cmp(x,y), filt_exp = lambda x: True, template_file = 'studentlist.html', extra_func = lambda x: {}):
        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self, 'program': prog}
        students = filter(filt_exp, filterObj.getList(ESPUser).distinct())
        for s in students:
            extra_dict = extra_func(s)
            for key in extra_dict:
                setattr(s, key, extra_dict[key])
        students.sort(sort_exp)
        context['students'] = students

        return render_to_response(self.baseDir()+template_file, request, context)

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
        from esp.accounting.models import Transfer
        #   Determine line item
        student_ids = []
        if 'id' in request.GET:
            lit_id = request.GET['id']
            request.session['li_type_id'] = lit_id
        else:
            lit_id = request.session['li_type_id']

        line_items = Transfer.objects.filter(line_item__id=lit_id)
        for l in line_items:
            student_ids.append(l.user_id)

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
            classes = [cls for cls in teacher.getTaughtSections()
                    if cls.parent_program == self.program
                    and cls.meeting_times.all().exists()
                    and cls.resourceassignment_set.all().exists()
                    and cls.status > 0]
            # now we sort them by time/title
            classes.sort()
            for cls in classes:
                scheditems.append({'name': teacher.name(),
                                   'teacher': teacher,
                                   'cls' : cls})

        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'teacherschedule.html', request, context)

    @aux_call
    @needs_admin
    def volunteerschedules(self, request, tl, one, two, module, extra, prog):
        """ generate volunteer schedules """

        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj

        context = {'module': self     }
        volunteers = list(filterObj.getList(ESPUser).distinct())
        volunteers.sort()

        scheditems = []

        for volunteer in volunteers:
            # get list of volunteer offers
            items = []
            offers = VolunteerOffer.objects.filter(user=volunteer, request__program=self.program)
            for offer in offers:
                items.append({'name': volunteer.name(),
                                   'volunteer': volunteer,
                                   'offer' : offer})
            #sort offers
            items.sort(key=lambda item: item['offer'].request.timeslot.start)
            #combine offers of all volunteers
            scheditems.extend(items)

        context['scheditems'] = scheditems

        return render_to_response(self.baseDir()+'volunteerschedule.html', request, context)

    def get_msg_vars(self, user, key):
        if key == 'receipt':
            #   Take the user's most recent registration profile.
            from esp.middleware.threadlocalrequest import AutoRequestContext as Context
            from django.conf import settings
            prof = user.getLastProfile()

            iac = IndividualAccountingController(self.program, user)

            context = {'program': self.program, 'user': self.user}

            payment_type = iac.default_payments_lineitemtype()
            context['itemizedcosts'] = iac.get_transfers().exclude(line_item=payment_type).order_by('-line_item__required')
            context['itemizedcosttotal'] = iac.amount_due()
            context['subtotal'] = iac.amount_requested()
            context['financial_aid'] = iac.amount_finaid()
            context['amount_paid'] = iac.amount_paid()

            return render_to_string(self.baseDir() + 'accounting_receipt.txt', context)

        if key == 'schedule':
            #   Generic schedule function kept for backwards compatibility
            return ProgramPrintables.getSchedule(self.program, user)
        elif key == 'student_schedule':
            return ProgramPrintables.getSchedule(self.program, user, u'Student')
        elif key == 'student_schedule_norooms':
            return ProgramPrintables.getSchedule(self.program, user, u'Student', room_numbers=False)
        elif key == 'teacher_schedule':
            return ProgramPrintables.getSchedule(self.program, user, u'Teacher')
        elif key == 'teacher_schedule_dates':
            return ProgramPrintables.getSchedule(self.program, user, u'Teacher', include_date=True)
        elif key == 'volunteer_schedule':
            return ProgramPrintables.getSchedule(self.program, user, u'Volunteer')
        elif key == 'volunteer_schedule_dates':
            return ProgramPrintables.getSchedule(self.program, user, u'Volunteer', include_date=True)
        elif key == 'transcript':
            return ProgramPrintables.getTranscript(self.program, user, 'text')
        elif key == 'transcript_html':
            return ProgramPrintables.getTranscript(self.program, user, 'html')
        elif key == 'transcript_latex':
            return ProgramPrintables.getTranscript(self.program, user, 'latex')

        return u''

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
                    and cls.meeting_times.exists()
                    and cls.status >= 0                       ]
        classes.sort()
        return classes

    @staticmethod
    def getTranscript(program, student, format='text'):
        from django.template import Template
        from esp.middleware.threadlocalrequest import AutoRequestContext as Context

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
    def getSchedule(program, user, schedule_type=None, room_numbers=True, include_date=False):

        if schedule_type is None:
            if user.isStudent():
                schedule_type = u'Student'
            elif user.isTeacher():
                schedule_type = u'Teacher'
            elif user.isVolunteer():
                schedule_type = u'Volunteer'


        if schedule_type == u'Student':
            template = get_template('program/modules/programprintables/studentschedule_email.html')
            sched_items = ProgramPrintables.get_student_classlist(program, user)
            sched_items.sort()
        elif schedule_type == u'Teacher':
            template = get_template('program/modules/programprintables/teacherschedule_email.html')
            sched_items = ProgramPrintables.get_teacher_classlist(program, user)
            sched_items.sort()
        elif schedule_type == u'Volunteer':
            template = get_template('program/modules/programprintables/volunteerschedule_email.html')
            sched_items = user.volunteeroffer_set.filter(request__program=program).order_by('request__timeslot__start')

        context = {
                   'program': program,
                   'user': user,
                   'schedule_type': schedule_type,
                   'room_numbers': room_numbers,
                   'include_date': include_date,
                   'sched_items': sched_items,
                   }
        schedule = template.render(context)

        return mark_safe(schedule)


    @aux_call
    @needs_admin
    def onsiteregform(self, request, tl, one, two, module, extra, prog):

        # Hack together a pseudocontext:
        context = { 'onsiteregform': True,
                    'students': [{'classes': [{'friendly_times': [prog.name],
                                               'classrooms': [''],
                                               'prettyrooms': ['______'],
                                               'title': '________________________________________',
                                               'getTeacherNames': [' ']} for i in prog.getTimeSlots()]}]
                    }
        return render_to_response(self.baseDir()+'studentschedule.html', request, context)

    @aux_call
    @needs_admin
    def student_financial_spreadsheet(self, request, tl, one, two, module, extra, prog, onsite=False):
        if onsite:
            students = [ESPUser.objects.get(id=request.GET['userid'])]
        else:
            filterObj, found = UserSearchController().create_filter(request, self.program)

            if not found:
                return filterObj

            students = list(ESPUser.objects.filter(filterObj.get_Q()).distinct())

        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow(('Control ID', 'Student ID', 'Last name', 'First name', 'Total cost', 'Finaid grant', 'Amount paid', 'Amount owed'))
        for student in students:
            iac = IndividualAccountingController(self.program, student)
            writer.writerow((iac.get_id(), student.id, student.last_name.encode('ascii', 'replace'), student.first_name.encode('ascii', 'replace'), '%.2f' % iac.amount_requested(), '%.2f' % iac.amount_finaid(), '%.2f' % iac.amount_paid(), '%.2f' % iac.amount_due()))

        return response

    @aux_call
    @needs_onsite_no_switchback
    def studentschedules(self, request, tl, one, two, module, extra, prog, onsite=False):

        context = {'module': self }

        if onsite:
            students = [ESPUser.objects.get(id=request.GET['userid'])]
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

        if extra:
            file_type = extra.strip()
        elif 'img_format' in request.GET:
            file_type = request.GET['img_format']
        else:
            if onsite:
                file_type = 'png'
            else:
                file_type = 'pdf'

        if len(students) > 1 and file_type == 'png':
            # Generating PNG schedules for a lot of students will cause
            # `convert` to use a huge amount of memory and make the server sad.
            # It also doesn't work, since we just return the first page of the
            # PNG anyway.  So don't let people do that.
            raise ESPError("Generating multi-page schedules in PNG format is "
                           "not supported.")

        # to avoid a query per student, get all the classes and SRs upfront
        all_classes = ClassSection.objects.filter(
            nest_Q(StudentRegistration.is_valid_qobject(),
                   'studentregistration'),
            studentregistration__user__in=students,
            studentregistration__relationship__name='Enrolled',
            parent_class__parent_program=prog,
            status=ACCEPTED,
            meeting_times__isnull=False).distinct()
        all_classes = all_classes.select_related('parent_class')
        all_classes = all_classes.prefetch_related('meeting_times')
        classes_by_id = {cls.id: cls for cls in all_classes}

        sr_pairs = all_classes.values_list('id', 'studentregistration__user')
        classes_by_student = collections.defaultdict(list)
        for cls_id, user_id in sr_pairs:
            classes_by_student[user_id].append(classes_by_id[cls_id])

        for user_id in classes_by_student:
            # Sort the classes.  We don't want to use __cmp__ because it will
            # not take advantage of our prefetching of meeting_times.
            classes_by_student[user_id].sort(
                key=lambda cls: (cls.start_time_prefetchable(), cls.title()))

        times_compulsory = Event.objects.filter(program=prog, event_type__description='Compulsory').order_by('start')
        for t in times_compulsory:
            t.friendly_times = [t.pretty_time()]
            t.initial_rooms = []

        show_empty_blocks = Tag.getBooleanTag('studentschedule_show_empty_blocks', prog)
        timeslots = list(prog.getTimeSlots())
        for student in students:
            student.updateOnsite(request)
            # get list of valid classes
            classes = classes_by_student[student.id]

            #get the student's last class on each day
            last_classes = []
            days = {}
            for cls in classes:
                date = cls.end_time_prefetchable().date().isocalendar()
                if date in days:
                    days[date].append(cls)
                else:
                    days[date]=[cls]

            for day,day_classes in days.items():
                last_classes.append(day_classes[-1])
            last_classes.sort()

            if show_empty_blocks:
                #   If you want to show empty blocks, start with a list of blocks instead
                #   and replace with classes where appropriate.
                times = timeslots[:]
                for cls in classes:
                    index = 0
                    for t in cls.meeting_times.all():
                        if t in times:
                            index = times.index(t)
                            times.remove(t)
                    times.insert(index, cls)
                classes = times

            #   Insert entries for the compulsory timeblocks into the schedule
            min_index = 0
            for t in times_compulsory:
                i = min_index
                while i < len(classes):
                    if isinstance(classes[i], Event):
                        start_time = classes[i].start
                    else:
                        start_time = classes[i].start_time_prefetchable()
                    if start_time > t.start:
                        classes.insert(i, t)
                        break
                    i += 1
                else:
                    classes.append(t)
                min_index = i

            # get payment information
            iac = IndividualAccountingController(prog, student)

            # attach payment information to student
            student.invoice_id = iac.get_id()
            student.itemizedcosts = iac.get_transfers()
            student.meals = iac.get_transfers(optional_only=True)  # catch everything that's not admission to the program.
            student.admission = iac.get_transfers(required_only=True)  # Program admission
            student.paid_online = iac.has_paid()
            student.amount_finaid = iac.amount_finaid()
            student.amount_siblingdiscount = iac.amount_siblingdiscount()
            student.itemizedcosttotal = iac.amount_due()

            student.has_paid = ( student.itemizedcosttotal == 0 )
            student.payment_info = True
            student.classes = classes
            student.last_classes = last_classes

        context['students'] = students
        context['program'] = prog

        from django.conf import settings
        context['PROJECT_ROOT'] = settings.PROJECT_ROOT.rstrip('/') + '/'

        basedir = 'program/modules/programprintables/'
        if file_type == 'html':
            return render_to_response(basedir+'studentschedule.html', request, context)
        else:  # elif format == 'pdf':
            return render_to_latex(basedir+'studentschedule.tex', context, file_type)

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

        return render_to_response(self.baseDir()+'flatstudentschedule.html', request, context)

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
                    if room.name in rooms:
                        rooms[room.name].append(update_dict)
                    else:
                        rooms[room.name] = [update_dict]

        for room_name in sorted(rooms.keys()):
            rooms[room_name].sort(key=lambda x: x['timeblock'].start)
            for val in rooms[room_name]:
                scheditems.append(val)

        context['scheditems'] = scheditems
        context['settings'] = settings
        context['group_name'] = Tag.getTag('full_group_name')
        context['phone_number'] = Tag.getTag('group_phone_number')

        return render_to_response(self.baseDir()+'roomrosters.html', request, context)

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

        return render_to_response(self.baseDir()+'student_tickets.html', request, context)

    @aux_call
    @needs_admin
    def classrosters(self, request, tl, one, two, module, extra, prog):
        """ generate class rosters """


        filterObj, found = UserSearchController().create_filter(request, self.program)
        if not found:
            return filterObj



        context = {'module': self, 'program': prog}
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

        return render_to_response(self.baseDir()+tpl, request, context)

    @aux_call
    @needs_admin
    def teacherlabels(self, request, tl, one, two, module, extra, prog):
        context = {'module': self}
        teachers = list(self.program.teachers()['class_approved'])
        teachers.sort()
        context['teachers'] = teachers
        context['settings'] = settings
        return render_to_response(self.baseDir()+'teacherlabels.html', request, context)

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
            finaid_status = 'None'
            if student.appliedFinancialAid(prog):
                if student.financialaidrequest_set.filter(program=prog).order_by('-id')[0].reduced_lunch:
                    finaid_status = 'Req. (RL)'
                else:
                    finaid_status = 'Req. (No RL)'

            iac = IndividualAccountingController(self.program, student)
            if student.hasFinancialAid(self.program):
                finaid_status = 'Approved'

            studentList.append({'user': student,
                                'paid': Record.user_completed(student, "paid", self.program) or iac.has_paid(in_full=True),
                                'amount_due': iac.amount_due(),
                                'finaid': finaid_status,
                                'checked_in': Record.user_completed(student, "attended",self.program),
                                'med': Record.user_completed(student, "med", self.program),
                                'liab': Record.user_completed(student, "liab", self.program)})

        context['students'] = students
        context['studentList'] = studentList
        return render_to_response(self.baseDir()+'studentchecklist.html', request, context)

    @aux_call
    @needs_admin
    def classchecklists(self, request, tl, one, two, module, extra, prog):
        """ Gives you a checklist for each classroom with the students that are supposed to be in that
            classroom.  The form has boxes for payment and forms.  This is useful for the first day
            of a program. """
        context = {'module': self, 'program': prog}

        students= [ user for user in self.program.students()['confirmed']]
        students.sort()

        class_list = []

        for c in self.program.classes():
            class_dict = {'cls': c}
            student_list = []

            for student in students:
                if c in student.getEnrolledClasses(self.program):
                    iac = IndividualAccountingController(self.program, student)
                    if iac.amount_due() <= 0:
                        paid_symbol = 'X'
                    else:
                        paid_symbol = ''
                    student_list.append({'user': student, 'paid': paid_symbol})

            class_dict['students'] = student_list
            class_list.append(class_dict)

        context['class_list'] = class_list

        return render_to_response(self.baseDir()+'classchecklists.html', request, context)

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
            return render_to_response(self.baseDir()+'adminteachers.html', request, context)



        if extra == 'classid':
            classes = [cls for cls in self.program.classes()
                       if cls.isAccepted()                   ]

            classes.sort(ClassSubject.idcmp)

            for cls in classes:
                for teacher in cls.get_teachers():
                    scheditems.append({'teacher': teacher,
                                      'class'  : cls})
            context['scheditems'] = scheditems
            return render_to_response(self.baseDir()+'adminclassid.html', request, context)


        if extra == 'timeblock':
            classes = [cls for cls in self.program.classes()
                       if cls.isAccepted()                   ]

            classes.sort()

            for cls in classes:
                for teacher in cls.get_teachers():
                    scheditems.append({'teacher': teacher,
                                      'cls'  : cls})

            context['scheditems'] = scheditems
            return render_to_response(self.baseDir()+'adminclasstime.html', request, context)

    @aux_call
    @needs_admin
    def certificate(self, request, tl, one, two, module, extra, prog):
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
        form = AllClassesSelectionForm()
        converter = form.converter

        if request.method == 'POST':
            form = AllClassesSelectionForm(request.POST)
            if form.is_valid():
                response = HttpResponse(content_type="text/csv")
                write_cvs = csv.writer(response)
                selected_fields = form.cleaned_data['subject_fields']
                csv_headings = [_encode_ascii(converter.field_dict[fieldname]) for fieldname in selected_fields]
                write_cvs.writerow(csv_headings)

                for cls in ClassSubject.objects.filter(parent_program=prog):
                    write_cvs.writerow([_encode_ascii(converter.fieldvalue(cls,f)) for f in selected_fields])

                response['Content-Disposition'] = 'attachment; filename=all_classes.csv'
                return response

        context = {}
        context['form'] = form
        return render_to_response(self.baseDir()+'all_classes_select_fields.html', request, context)

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

        response = HttpResponse(content_type="text/csv")
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

        if Tag.getBooleanTag('oktimes_collapse'):
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
            if Tag.getBooleanTag('oktimes_collapse'):
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
        from esp.resources.models import ResourceType

        response = HttpResponse(content_type="text/csv")
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
            teachers = section.parent_class.get_teachers()
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
        from esp.resources.models import ResourceAssignment
        response = HttpResponse(content_type="text/csv")
        write_csv = csv.writer(response)

        data = ResourceAssignment.objects.filter(target__parent_class__parent_program=prog).order_by('target__id', 'resource__event__id').values_list('target__id', 'resource__name', 'resource__event__id', 'lock_level')
        for row in data:
            write_csv.writerow(row)

        response['Content-Disposition'] = 'attachment; filename=csv_schedule.csv'
        return response

    class Meta:
        proxy = True
        app_label = 'modules'


class AllClassesFieldConverter(object):
    """
    Handles value extraction and formatting of CLassSubject instances. This is
    used as 'pre-processing' step when generating the records for the All Classes
    CSV spreadsheet.
    """
    TEACHERS = 'teachers'
    TIMES = 'times'
    ROOMS = 'rooms'
    NUM_SECTIONS = "number of sections"
    exclude_fields = ['session_count']

    def __init__(self):
        field_list = [field for field in ClassSubject._meta.fields if field.name not in self.exclude_fields]
        #field_list.sort(key=lambda x: x.name)
        self.field_choices = [(f, f.title()) for f in (self.TEACHERS, self.TIMES, self.ROOMS, self.NUM_SECTIONS)]
        self.field_choices += [(field.name, field.verbose_name.title()) for field in field_list]

        #sort tuple list by field name
        sorted(self.field_choices,key=lambda x: x[0])
        self.field_dict = dict(self.field_choices)

        #a dict of field names and asscoiated formatting lambdas to handle generation
        #of field data that should have a different format than the default.
        self.field_converters = {
            self.TEACHERS: lambda x: ", ".join([smart_str(t.name()) for t in x.get_teachers()]),
            self.TIMES: lambda x: ", ".join(x.friendly_times()),
            self.ROOMS: lambda x: ", ".join(x.prettyrooms()),
            self.NUM_SECTIONS: lambda x: x.sections.count()
        }

    def fieldvalue(self, class_subject, fieldname):
        """
        Returns the value of the specified field for the supplied class_subject instance.
        Fields that are defined in the field_converters dict will have an associated
        formatting function which will be executed to return the appropriate format.
        """
        fieldvalue = ''
        if fieldname in self.field_converters:
            fieldvalue = self.field_converters[fieldname](class_subject)
        elif hasattr(class_subject, fieldname):
            fieldvalue = getattr(class_subject, fieldname)
        else:
            raise ValueError('Invalid fieldname supplied {0}'.format(fieldname))
        return fieldvalue


class AllClassesSelectionForm(forms.Form):
    subject_fields = forms.MultipleChoiceField()

    def __init__(self, *args, **kwargs):
        super(AllClassesSelectionForm, self).__init__(*args, **kwargs)

        self.converter = AllClassesFieldConverter()
        self.fields['subject_fields'].choices = self.converter.field_choices
